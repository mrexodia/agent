#include <cstdlib>
#include <filesystem>
#include <string>

#include <fmt/format.h>
#include <args.hpp>

#include "utils.hpp"

#ifndef DOTENV
#error Missing DOTENV preprocessor definition.
#endif

struct Arguments : ArgumentParser {
  std::string model = "openai/gpt-oss-20b";

  Arguments(int argc, char** argv) : ArgumentParser("Agent CLI") {
    addString("--model", model, "Model to use for the agent (default: openai/gpt-oss-20b)");
    parseOrExit(argc, argv, "--help");
  }
};

int main(int argc, char **argv) {
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

  fmt::print("[System prompt]\n{}\n", utils::SYSTEM_PROMPT);

  fmt::print("\n[Bash command: pwd]\n");
  auto [output, exit_code] = utils::bash_command(
    "pwd", std::filesystem::current_path()
  );
  fmt::print("{}\n", utils::strip(output));
  fmt::print("Exit code: {}\n", exit_code);

  auto response = utils::post_json(
    std::string(OPENAI_BASE_URL) + "/chat/completions",
    OPENAI_API_KEY,
    {
      {"model", args.model},
      {"messages",
       {{
         {"role", "user"},
         {"content", "Hello, world!"},
       }}},
    }
  );

  fmt::print("\n[OpenAI Response]\n");
  fmt::print("{}\n", response.dump(2));
  return 0;
}
