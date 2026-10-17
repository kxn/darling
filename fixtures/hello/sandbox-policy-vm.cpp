#include <darlingserver/sandbox-policy.hpp>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <unordered_map>
using namespace DarlingServer::Sandbox;
int main(int argc,char** argv) {
 if(argc!=2)return 2;
 std::unordered_map<std::string,std::shared_ptr<const Policy>> cache;
 std::string line;
 while(std::getline(std::cin,line)) {
  std::istringstream row(line);std::string name,operation,field,value;
  if(!std::getline(row,name,'\t')||!std::getline(row,operation,'\t'))return 3;
  if(!cache.count(name)) {
   std::ifstream f(std::string(argv[1])+"/"+name+".bin",std::ios::binary);
   if(!f){std::cout<<"parse-error:missing file\n";continue;}
   std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(f)),{});std::string error;cache[name]=Policy::parse(std::move(bytes),error);
   if(!cache[name]){std::cout<<"parse-error:"<<error<<'\n';cache.erase(name);continue;}
  }
  Context c;
  while(std::getline(row,field,'\t')) {
   auto pos=field.find('=');if(pos==std::string::npos)return 4;value=field.substr(pos+1);field.resize(pos);
   if(field=="path")c.path=value;
   else if(field=="global")c.globalName=value;
   else if(field=="local")c.localName=value;
   else if(field=="posix")c.posixName=value;
   else if(field=="control")c.controlName=value;
   else if(field=="iokitClass")c.iokitClass=value;
   else if(field=="iokitProperty")c.iokitProperty=value;
   else if(field=="preference")c.preferenceDomain=value;
   else if(field=="sysctl")c.sysctlName=value;
   else if(field=="xpc")c.xpcServiceName=value;
   else if(field=="self")c.targetSelf=value=="1";
   else if(field=="debug")c.systemAttributes=value=="1"?2:0;
   else if(field=="systemAttributes")c.systemAttributes=std::stoull(value);
   else if(field=="attributes")c.processAttributes=std::stoull(value);
   else if(field=="vnode")c.vnodeType=std::stoul(value);
   else if(field=="absent")c.knownAbsentFilters=std::stoull(value);
   else if(field=="fsctl")c.fsctlBaseCommand=std::stoul(value);
   else return 5;
  }
  auto d=cache[name]->evaluate(operation,c);
  std::cout<<(d==Decision::Allow?"allow":d==Decision::Deny?"deny":"unsupported")<<'\n';
 }
}
