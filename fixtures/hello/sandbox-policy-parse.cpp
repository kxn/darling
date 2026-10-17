#include <darlingserver/sandbox-policy.hpp>
#include <iostream>
#include <string>
#include <vector>
using namespace DarlingServer::Sandbox;
int main() {
 std::string text;
 while(std::getline(std::cin,text)) {
  std::vector<uint8_t> bytes;
  if(text.size()%2)return 2;
  auto digit=[](char c)->int {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;return -1;};
  for(size_t i=0;i<text.size();i+=2){int a=digit(text[i]),b=digit(text[i+1]);if(a<0||b<0)return 3;bytes.push_back((a<<4)|b);}
  std::string error;auto policy=Policy::parse(std::move(bytes),error);
  if(!policy)std::cout<<"reject\t"<<error<<'\n';
  else {
   Context c;c.path="/tmp/check";c.knownAbsentFilters=~uint64_t(2);c.systemAttributes=0;c.processAttributes=0;c.targetSelf=true;c.vnodeType=1;c.fsctlBaseCommand=0;
   for(size_t i=0;i<198;i++)(void)policy->evaluate(Policy::operationName(i),c);
   std::cout<<"accept\t"<<policy->nodeCount()<<'\n';
  }
 }
}
