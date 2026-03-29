#include <cstdlib>
#include <exception>
#include <filesystem>
#include <string>

#include <args.hpp>
#include <fmt/format.h>

#include "constants.hpp"
#include "utils.hpp"

using json = nlohmann::json;

#ifndef DOTENV
#error Missing DOTENV preprocessor definition.
#endif

struct Arguments : ArgumentParser {
  std::string model = "openai/gpt-oss-20b";
  std::filesystem::path cwd = std::filesystem::current_path();

  Arguments(int argc, char **argv) : ArgumentParser("Agent CLI") {
    addString(
      "--model",
      model,
      "Model to use for the agent (default: openai/gpt-oss-20b)"
    );
    std::string cwd_str;
    addString(
      "--cwd", cwd_str, "Working directory (default: current directory)"
    );
    parseOrExit(argc, argv, "--help");
    if (!cwd_str.empty()) {
      cwd = cwd_str;
    }
  }
};

static int run(int argc, char **argv) {
  utils::load_dotenv(DOTENV);

  auto OPENAI_BASE_URL = std::getenv("OPENAI_BASE_URL");
  if (!OPENAI_BASE_URL) {
    fmt::print("OPENAI_BASE_URL environment variable is not set\n");
    return 1;
  }

  auto OPENAI_API_KEY = std::getenv("OPENAI_API_KEY");
  if (!OPENAI_API_KEY) {
    fmt::print("OPENAI_API_KEY environment variable is not set\n");
    return 1;
  }

  Arguments args(argc, argv);

  fmt::print("[System prompt]\n{}\n", constants::SYSTEM_PROMPT);

  fmt::print("\n[Bash command: pwd]\n");
  auto [output, exit_code] = utils::bash_command("pwd", args.cwd);
  fmt::print("{}\n", utils::strip(output));
  fmt::print("Exit code: {}\n", exit_code);

  auto messages = json::array();
  messages.push_back({
    {"role", "system"},
    {"content", constants::SYSTEM_PROMPT},
  });
  messages.push_back({
    {"role", "user"},
    {"content", "Hello, world!"},
  });

  auto response = utils::post_json(
    std::string(OPENAI_BASE_URL) + "/chat/completions",
    OPENAI_API_KEY,
    {
      {"model", args.model},
      {"messages", messages},
      {"tools", constants::TOOL_DEFINITIONS},
    }
  );

  fmt::print("\n[OpenAI Response]\n");
  fmt::print("{}\n", response.dump(2));
  return EXIT_SUCCESS;
}

int main(int argc, char **argv) {
  try {
    return run(argc, argv);
  } catch (const std::exception &e) {
    puts(e.what());
    return EXIT_FAILURE;
  }
}
