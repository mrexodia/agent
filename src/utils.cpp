#include "utils.hpp"

#include <chrono>
#include <cstdlib>
#include <fstream>
#include <stdexcept>
#include <vector>

#include <fmt/chrono.h>
#include <fmt/format.h>
#include <httplib.h>
#include <reproc/drain.h>
#include <reproc/reproc.h>

namespace fs = std::filesystem;

namespace {

fs::path LOG_DIR = [] {
  auto env_log_dir = std::getenv("AGENT_LOG_DIR");
  fs::path dir = env_log_dir ? env_log_dir : ".agent-logs";
  auto now = std::chrono::floor<std::chrono::seconds>(
    std::chrono::system_clock::now()
  );
  dir /= fmt::format("{:%Y-%m-%d_%H-%M-%S}", now);
  return dir;
}();

fs::path find_in_path(const std::vector<std::string> &names) {
  const char *path_env = std::getenv("PATH");
  if (!path_env)
    return {};

#ifdef _WIN32
  constexpr char separator = ';';
#else
  constexpr char separator = ':';
#endif

  std::string path_value(path_env);
  size_t start = 0;
  while (start <= path_value.size()) {
    auto end = path_value.find(separator, start);
    std::string entry = end == std::string::npos
                          ? path_value.substr(start)
                          : path_value.substr(start, end - start);

    if (!entry.empty()) {
      fs::path base(entry);
      for (const auto &name : names) {
        auto candidate = base / name;
        if (fs::exists(candidate)) {
          return fs::absolute(candidate).lexically_normal();
        }
      }
    }

    if (end == std::string::npos)
      break;
    start = end + 1;
  }

  return {};
}

const fs::path &bash_path() {
  static const fs::path path = [] {
#ifdef _WIN32
    auto git_path = find_in_path({"git.exe", "git.cmd", "git.bat", "git"});
    if (git_path.empty()) {
      throw std::runtime_error("Git is not installed or not in PATH");
    }

    auto bash = fs::absolute(
                  git_path.parent_path() / ".." / ".." / "bin" / "bash.exe"
    )
                  .lexically_normal();
#else
    fs::path bash = "/bin/bash";
#endif

    if (!fs::exists(bash)) {
      throw std::runtime_error(
        fmt::format("Bash not found at {}", bash.string())
      );
    }

    return bash;
  }();

  return path;
}

std::runtime_error reproc_error(const std::string &context, int error) {
  return std::runtime_error(
    fmt::format("{}: {}", context, reproc_strerror(error))
  );
}

void split_url(
  const std::string &url,
  std::string &scheme_host_port,
  std::string &path
) {
  auto pos = url.find("://");
  if (pos == std::string::npos) {
    scheme_host_port = url;
    path = "/";
  } else {
    auto path_pos = url.find('/', pos + 3);
    if (path_pos != std::string::npos) {
      scheme_host_port = url.substr(0, path_pos); // "https://api.openai.com"
      path = url.substr(path_pos);                // "/v1/chat/completions"
    } else {
      scheme_host_port = url;
      path = "/";
    }
  }
}

void log_json(const nlohmann::json &j, const std::string &filename) {
  if (!fs::exists(LOG_DIR)) {
    std::error_code ec;
    fs::create_directories(LOG_DIR, ec);
    if (ec) {
      fmt::print(
        stderr,
        "Warning: Failed to create log directory {}: {}\n",
        LOG_DIR.string(),
        ec.message()
      );
      return;
    }
    std::ofstream(LOG_DIR.parent_path() / ".gitignore") << "*\n";
  }
  std::ofstream(LOG_DIR / filename) << j.dump(2);
}

} // namespace

namespace utils {

std::string strip(std::string value) {
  constexpr auto whitespace = " \t\n\r\f\v";
  auto start = value.find_first_not_of(whitespace);
  if (start == std::string::npos)
    return {};

  auto end = value.find_last_not_of(whitespace);
  return value.substr(start, end - start + 1);
}

void load_dotenv(const fs::path &dotenv_path) {
  std::ifstream dotenv(dotenv_path);
  if (!dotenv.is_open())
    return;

  std::string line;
  while (std::getline(dotenv, line)) {
    // trim trailing \r (Windows line endings)
    if (!line.empty() && line.back() == '\r')
      line.pop_back();

    // skip empty lines and comments
    if (line.empty() || line[0] == '#')
      continue;

    auto eq = line.find('=');
    if (eq == std::string::npos)
      continue;

    auto key = line.substr(0, eq);
    auto value = line.substr(eq + 1);

    // strip optional quotes
    if (value.size() >= 2 &&
        ((value.front() == '"' && value.back() == '"') ||
         (value.front() == '\'' && value.back() == '\''))) {
      value = value.substr(1, value.size() - 2);
    }

    // don't overwrite existing environment variables
#ifdef _WIN32
    size_t len = 0;
    getenv_s(&len, nullptr, 0, key.c_str());
    if (len == 0) {
      _putenv_s(key.c_str(), value.c_str());
    }
#else
    setenv(key.c_str(), value.c_str(), 0);
#endif
  }
}

std::pair<std::string, int> bash_command(
  const std::string &command,
  fs::path cwd,
  int timeout
) {
  auto bash = bash_path().string();
  auto cwd_string = cwd.string();
  const char *argv[] = {bash.c_str(), "-c", command.c_str(), nullptr};

  reproc_options options{};
  options.working_directory = cwd_string.c_str();
  options.redirect.in.type = REPROC_REDIRECT_PARENT;
  options.redirect.out.type = REPROC_REDIRECT_PIPE;
  options.redirect.err.type = REPROC_REDIRECT_STDOUT;
  if (timeout >= 0) {
    options.deadline = timeout * 1000;
  }

  reproc_t *process = reproc_new();
  if (!process) {
    throw std::runtime_error("Failed to allocate process");
  }

  char *output = nullptr;
  int exit_status = -1;

  auto cleanup = [&] {
    reproc_destroy(process);
    reproc_free(output);
  };

  int r = reproc_start(process, argv, options);
  if (r < 0) {
    cleanup();
    throw reproc_error(fmt::format("Failed to start '{}'", bash), r);
  }

  auto sink = reproc_sink_string(&output);
  r = reproc_drain(process, sink, REPROC_SINK_NULL);
  if (r < 0) {
    if (r == REPROC_ETIMEDOUT) {
      reproc_kill(process);
      reproc_wait(process, REPROC_INFINITE);
      auto partial_output = std::string(output ? output : "");
      cleanup();
      throw std::runtime_error(
        fmt::format(
          "Command timed out after {} seconds: {}\n{}",
          timeout,
          command,
          partial_output
        )
      );
    }

    reproc_kill(process);
    reproc_wait(process, REPROC_INFINITE);
    cleanup();
    throw reproc_error(
      fmt::format("Failed to read output for '{}'", command), r
    );
  }

  exit_status = reproc_wait(process, REPROC_INFINITE);
  if (exit_status < 0) {
    cleanup();
    throw reproc_error(
      fmt::format("Failed to wait for '{}'", command), exit_status
    );
  }

  std::string result = output ? output : "";
  cleanup();
  return {result, exit_status};
}

nlohmann::json post_json(
  const std::string &url,
  const std::string &bearer,
  const nlohmann::json &payload
) {
  static uint64_t request_counter = 0;
  uint64_t request_id = ++request_counter;
  log_json(payload, fmt::format("{}_request.json", request_id));
  std::string scheme_host_port, path;
  split_url(url, scheme_host_port, path);
  httplib::Client cli(scheme_host_port);
  httplib::Headers headers{
    {"Authorization", "Bearer " + bearer},
    {"Content-Type", "application/json"},
  };
  httplib::Result response = cli.Post(
    path, headers, payload.dump(), "application/json"
  );
  if (!response) {
    throw std::runtime_error(
      fmt::format(
        "HTTP POST {} failed: {}", url, httplib::to_string(response.error())
      )
    );
  }

  if (response->status != 200) {
    std::string error_message;
    try {
      auto error = nlohmann::json::parse(response->body);
      log_json(error, fmt::format("{}_response.json", request_id));
      error_message = fmt::format(
        "HTTP POST {} failed with status {}:\n{}",
        url,
        response->status,
        error.dump(2)
      );
    } catch (const std::exception &) {
      error_message = fmt::format(
        "HTTP POST {} failed with status {}: {}",
        url,
        response->status,
        response->body
      );
      // Fall back to raw body if JSON parsing fails
    }
    throw std::runtime_error(error_message);
  }
  try {
    auto result = nlohmann::json::parse(response->body);
    log_json(result, fmt::format("{}_response.json", request_id));
    return result;
  } catch (const std::exception &e) {
    throw std::runtime_error(
      fmt::format("Failed to parse JSON response from {}: {}", url, e.what())
    );
  }
}

} // namespace utils
