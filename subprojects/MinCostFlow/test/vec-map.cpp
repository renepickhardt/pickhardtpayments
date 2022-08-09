#include <mincostflow/vectorized_map.hpp>

#define CHECK(cond) \
    if(!(cond)) return 1;
        

int main()
{
    ln::vectorized_map<std::size_t,int> vm;
    
    // initial state
    CHECK(vm.capacity()==0 && vm.size()==0);
    
    // add three elements
    vm.insert(1);
    vm.insert(2);
    vm.insert(3);
    CHECK(vm.capacity()==3 && vm.size()==3);
    
    // remove the first
    vm.erase(0);
    CHECK(vm.capacity()==3 && vm.size()==2);
    
    // remove twice, no effect
    vm.erase(0);
    CHECK(vm.capacity()==3 && vm.size()==2);
    
    // add a new one, to the first empty slot
    vm.insert(11);
    CHECK(vm.capacity()==3 && vm.size()==3);
    
    // remove a non-existent index, no effect
    vm.erase(4);
    CHECK(vm.capacity()==3 && vm.size()==3);
    
    // remove from the tail, effect capacity changes
    vm.erase(1);
    vm.erase(2);
    CHECK(vm.capacity()==1 && vm.size()==1);
    return 0; 
}
