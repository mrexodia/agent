#include "utils.hpp"

#include <stdexcept>

#include <fmt/format.h>
#include <httplib.h>

namespace utils {

void load_dotenv(const std::filesystem::path &dotenv_path) {
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

std::string bash_command(
  const std::string &command,
  std::filesystem::path cwd,
  int timeout
) {
  return {};
}

static void split_url(
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

nlohmann::json post_json(
  const std::string &url,
  const std::string &bearer,
  const nlohmann::json &payload
) {
  std::string scheme_host_port, path;
  split_url(url, scheme_host_port, path);
  httplib::Client cli(scheme_host_port);
  httplib::Headers headers{{"Authorization", "Bearer " + bearer}};
  httplib::Result response = cli.Post(
    path, headers, payload.dump(2), "application/json"
  );
  if (!response) {
    throw std::runtime_error(
      fmt::format(
        "HTTP POST {} failed: {}", url, httplib::to_string(response.error())
      )
    );
  }

  if (response->status != 200) {
    throw std::runtime_error(
      fmt::format(
        "HTTP POST {} returned status code {}: {}",
        url,
        response->status,
        response->body
      )
    );
  }
  try {
    return nlohmann::json::parse(response->body);
  } catch (const std::exception &e) {
    throw std::runtime_error(
      fmt::format("Failed to parse JSON response from {}: {}", url, e.what())
    );
  }
}

} // namespace utils
