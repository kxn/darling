#include <darlingserver/sandbox-policy.hpp>
#include <iostream>
#include <string>
#include <vector>
using namespace DarlingServer::Sandbox;
int main() {
    std::string line;
    while(std::getline(std::cin,line)) {
        std::vector<uint8_t> bytes;
        if(line.size()%2)return 2;
        for(size_t i=0;i<line.size();i+=2)bytes.push_back(std::stoul(line.substr(i,2),nullptr,16));
        std::string error;auto policy=Policy::parse(std::move(bytes),error);
        if(!policy) {std::cout<<"reject\n";continue;}
        if(policy->allowsAllOperations()) {
            for(size_t i=0;i<198;i++)if(policy->evaluate(Policy::operationName(i),{})!=Decision::Allow)return 3;
        }
        if(policy->evaluate("not-a-native-operation",{})!=Decision::Unsupported)return 4;
        std::cout<<(policy->allowsAllOperations()?"unrestricted":"restricted")<<'\n';
    }
}
