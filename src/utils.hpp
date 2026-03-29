#pragma once

#include <filesystem>
#include <nlohmann/json.hpp>
#include <string>
#include <utility>

namespace utils {

/// Trim leading and trailing ASCII whitespace from a string.
std::string strip(std::string value);

/// Load KEY=VALUE pairs from a .env file without overwriting existing
/// environment variables.
///
/// Missing files are ignored.
void load_dotenv(const std::filesystem::path &dotenv_path);

/// Execute `bash -c <command>` in `cwd` and return combined stdout/stderr with
/// the process exit code.
///
/// @param timeout Timeout in seconds. Pass a negative value to wait forever.
/// @throws std::runtime_error If bash cannot be located, the process cannot be
/// started, its output cannot be collected, waiting fails, or the timeout
/// expires.
std::pair<std::string, int> bash_command(
  const std::string &command,
  std::filesystem::path cwd,
  int timeout = -1
);

/// POST a JSON payload with bearer authentication and parse the JSON response.
///
/// @throws std::runtime_error If the HTTP request fails, the response status is
/// not 200, or the response body is not valid JSON.
nlohmann::json post_json(
  const std::string &url,
  const std::string &bearer,
  const nlohmann::json &payload
);

} // namespace utils
