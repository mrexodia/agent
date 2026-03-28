
#include <cstdlib>
#include <fmt/format.h>

#include "utils.hpp"

#ifndef DOTENV
#error Missing DOTENV preprocessor definition.
#endif

int main(int argc, char **argv) {
  utils::load_dotenv(DOTENV);

  auto OPENAI_ENDPOINT = std::getenv("OPENAI_ENDPOINT");
  if (!OPENAI_ENDPOINT) {
    fmt::print("OPENAI_ENDPOINT environment variable is not set\n");
    return 1;
  }

  auto OPENAI_BEARER_TOKEN = std::getenv("OPENAI_BEARER_TOKEN");
  if (!OPENAI_BEARER_TOKEN) {
    fmt::print("OPENAI_BEARER_TOKEN environment variable is not set\n");
    return 1;
  }

  auto response = utils::post_json(
    OPENAI_ENDPOINT + std::string("/chat/completions"),
    OPENAI_BEARER_TOKEN,
    {
      {"model", "openai/gpt-oss-20b"},
      {"messages",
       {{
         {"role", "user"},
         {"content", "Hello, world!"},
       }}},
    }
  );
  fmt::print("Response:\n{}\n", response.dump(2));
}
