#include <stdexcept>
#include <string>
#include <vector>

int main() {
    std::vector<std::string> names{"Darling", "Xcode", "Linux"};
    try {
        if (names.size() != 3) throw std::runtime_error("container failure");
        return names.at(1) == "Xcode" ? 0 : 1;
    } catch (const std::exception&) {
        return 2;
    }
}
