#include <darlingserver/fsevents-journal.hpp>
#include <sys/stat.h>
#include <fcntl.h>
#include <pthread.h>
#include <unistd.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <filesystem>
#include <mutex>
#include <thread>
#include <vector>
#include <stdexcept>
using namespace DarlingServer::FSEvents;
namespace fs=std::filesystem;
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"JOURNAL_FAIL %d %s errno=%d\n",__LINE__,#x,errno);abort();}}while(0)
struct Receiver {
    std::mutex mutex;
    std::vector<JournalEvent> values;
    std::atomic<bool> blocked{false};
    int accept(const JournalEvent& event){if(blocked)return 0;std::lock_guard lock(mutex);values.push_back(event);return 1;}
    std::vector<JournalEvent> take(){std::lock_guard lock(mutex);auto copy=values;values.clear();return copy;}
};
static void writeFile(const std::string& path){int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_TRUNC,0600);CHECK(fd>=0);CHECK(write(fd,"real",4)==4);CHECK(close(fd)==0);}
static std::vector<JournalEvent> ordinary(const std::vector<JournalEvent>& values){std::vector<JournalEvent> result;for(auto& e:values)if(e.flags!=JournalBarrierFlag)result.push_back(e);return result;}
static bool has(const std::vector<JournalEvent>& values,uint32_t flag,const std::string& path={}){return std::any_of(values.begin(),values.end(),[&](auto& e){return (e.flags&flag)&& (path.empty()||e.path==path);});}
static void barrier(Journal& journal,uint64_t sub,Receiver& receiver){uint64_t token=0;CHECK(journal.barrier(sub,token)==0);for(unsigned i=0;i<200;i++){bool found=false;{std::lock_guard lock(receiver.mutex);for(auto& e:receiver.values)if(e.flags==JournalBarrierFlag&&e.id>=token)found=true;}if(found)return;usleep(1000);}CHECK(false);}
struct SmallStack {Journal* journal;std::string root;};
static void* smallStack(void* value){auto* context=static_cast<SmallStack*>(value);uint64_t current=0;CHECK(context->journal->current(current)==0);Receiver receiver;uint64_t sub=0;CHECK(context->journal->subscribe({{context->root,"/"}},current,0x10,[&](auto& e){return receiver.accept(e);},sub)==0);barrier(*context->journal,sub,receiver);context->journal->unsubscribe(sub);return nullptr;}
int main(){setbuf(stdout,nullptr);char temporary[]="/tmp/fsevents-global.XXXXXX";CHECK(mkdtemp(temporary));std::string base=temporary,root=base+"/root",outside=base+"/outside",state=base+"/counter";fs::create_directory(root);fs::create_directory(outside);uint64_t last=0;
 {
    Journal journal(state,{{root,"/"}},16);uint64_t first=0;CHECK(journal.current(first)==0&&first>0);
    SmallStack small{&journal,root};pthread_attr_t attribute;CHECK(!pthread_attr_init(&attribute));CHECK(!pthread_attr_setstacksize(&attribute,64*1024));pthread_t thread;CHECK(!pthread_create(&thread,&attribute,smallStack,&small));CHECK(!pthread_attr_destroy(&attribute));CHECK(!pthread_join(thread,nullptr));
    for(unsigned i=0;i<32;i++){uint64_t value=0;CHECK(journal.current(value)==0&&value==first);}
    bool exclusive=false;try{Journal other(state,{{root,"/"}});}catch(const std::system_error& e){exclusive=e.code().value()==EAGAIN||e.code().value()==EWOULDBLOCK;}CHECK(exclusive);
    Receiver one,two;uint64_t a=0,b=0;
    CHECK(journal.subscribe({{root,"/one"}},UINT64_MAX,0x10,[&](auto& e){return one.accept(e);},a)==0);
    CHECK(journal.subscribe({{root,"/two"}},UINT64_MAX,0x10,[&](auto& e){return two.accept(e);},b)==0);
    writeFile(root+"/file");barrier(journal,a,one);barrier(journal,b,two);
    auto left=ordinary(one.take()),right=ordinary(two.take());CHECK(!left.empty()&&left.size()==right.size());
    for(size_t i=0;i<left.size();i++){CHECK(left[i].id==right[i].id&&left[i].flags==right[i].flags);CHECK(left[i].path=="/one/file"&&right[i].path=="/two/file");CHECK(left[i].id>first);}
    CHECK(has(left,0x100)&&has(left,0x1000));uint64_t token=0;CHECK(journal.current(token)==0&&token>=left.back().id);
    journal.unsubscribe(a);journal.unsubscribe(b);writeFile(root+"/after-close");CHECK(journal.current(last)==0&&last>token);
    Receiver replay;uint64_t c=0;CHECK(journal.subscribe({{root,"/"}},token,0x10,[&](auto& e){return replay.accept(e);},c)==0);
    barrier(journal,c,replay);auto history=ordinary(replay.take());CHECK(has(history,0x100,"/after-close")&&history.back().flags==0x10);CHECK(!has(history,2));journal.unsubscribe(c);
    CHECK(journal.current(token)==0);CHECK(journal.subscribe({{root,"/"}},token,0,[&](auto& e){return replay.accept(e);},c)==0);barrier(journal,c,replay);history=ordinary(replay.take());CHECK(history.size()==1&&history[0].flags==0x10&&history[0].id==token);journal.unsubscribe(c);
    puts("JOURNAL_SHARED_IDS_STABLE_READS_CLOSE_AND_GENUINE_REPLAY_OK");
    fs::create_directories(root+"/parent/SDK");CHECK(journal.current(token)==0);
    CHECK(journal.subscribe({{root+"/parent/SDK","/sdk"}},UINT64_MAX,0x14,[&](auto& e){return replay.accept(e);},c)==0);
    fs::rename(root+"/parent",root+"/old-parent");barrier(journal,c,replay);history=ordinary(replay.take());CHECK(has(history,0x20,"/sdk"));journal.unsubscribe(c);
    fs::create_directories(root+"/parent/SDK");CHECK(journal.current(token)==0);
    CHECK(journal.subscribe({{root,"/"}},UINT64_MAX,0x10,[&](auto& e){return replay.accept(e);},c)==0);
    fs::create_directories(root+"/nested/a/b");writeFile(root+"/nested/a/b/raced");barrier(journal,c,replay);history=ordinary(replay.take());CHECK(has(history,1)&&has(history,2));
    writeFile(root+"/nested/a/b/later");barrier(journal,c,replay);history=ordinary(replay.take());CHECK(has(history,0x1000,"/nested/a/b/later"));
    fs::rename(root+"/nested",root+"/renamed");barrier(journal,c,replay);replay.take();writeFile(root+"/renamed/a/b/after-move");barrier(journal,c,replay);history=ordinary(replay.take());CHECK(has(history,0x1000,"/renamed/a/b/after-move"));
    fs::rename(root+"/renamed",outside+"/moved-out");usleep(150000);barrier(journal,c,replay);replay.take();writeFile(outside+"/moved-out/a/b/outside");barrier(journal,c,replay);CHECK(ordinary(replay.take()).empty());journal.unsubscribe(c);
    puts("JOURNAL_REAL_SUBTREE_CREATION_RENAME_AND_MOVE_OUT_OK");
    CHECK(journal.current(token)==0);for(unsigned i=0;i<64;i++)writeFile(root+"/evict-"+std::to_string(i));CHECK(journal.current(last)==0&&last>token+16);
    CHECK(journal.subscribe({{root,"/"}},token,0x10,[&](auto& e){return replay.accept(e);},c)==0);barrier(journal,c,replay);history=ordinary(replay.take());CHECK(has(history,2)&&history.back().flags==0x10);journal.unsubscribe(c);
    Receiver blocked;blocked.blocked=true;CHECK(journal.subscribe({{root,"/"}},UINT64_MAX,0x10,[&](auto& e){return blocked.accept(e);},c)==0);
    for(unsigned i=0;i<2200;i++)writeFile(root+"/pressure-"+std::to_string(i));CHECK(journal.current(last)==0);blocked.blocked=false;barrier(journal,c,blocked);history=ordinary(blocked.take());CHECK(has(history,2));journal.unsubscribe(c);
    CHECK(journal.current(last)==0);puts("JOURNAL_BOUNDED_HISTORY_AND_REAL_BACKPRESSURE_LOSS_OK");
 }
 {Journal restarted(state,{{root,"/"}});uint64_t current=0;CHECK(restarted.current(current)==0&&current>last);Receiver receiver;uint64_t sub=0;CHECK(restarted.subscribe({{root,"/"}},last,0x10,[&](auto& e){return receiver.accept(e);},sub)==0);barrier(restarted,sub,receiver);auto history=ordinary(receiver.take());CHECK(has(history,2)&&history.back().flags==0x10);}
 {auto inner=base+"/inside-state";fs::create_directory(inner);fs::create_directory_symlink(inner,base+"/state-alias");Journal self(base+"/state-alias/id",{{inner,"/"}});uint64_t token=0;CHECK(self.current(token)==0);for(unsigned i=0;i<32;i++){uint64_t value=0;CHECK(self.current(value)==0&&value==token);}}
 {auto watched=base+"/watch-root";fs::create_directory(watched);Journal watch(base+"/watch-id",{{watched,"/"}});Receiver receiver;uint64_t sub=0;CHECK(watch.subscribe({{watched,"/scope"}},UINT64_MAX,4,[&](auto& e){return receiver.accept(e);},sub)==0);fs::rename(watched,base+"/watch-moved");barrier(watch,sub,receiver);auto events=ordinary(receiver.take());CHECK(has(events,0x20,"/scope"));for(auto& e:events)if(e.flags&0x20)CHECK(e.id==0);}
 int fd=open(state.c_str(),O_WRONLY|O_TRUNC);CHECK(fd>=0);CHECK(write(fd,"bad",3)==3);close(fd);bool refused=false;try{Journal corrupt(state,{{root,"/"}});}catch(const std::system_error& e){refused=e.code().value()==EIO;}CHECK(refused);
 fs::remove_all(base);printf("FSEVENTS_SHARED_JOURNAL_LINUX_OK checks=%u\n",checks);
}
