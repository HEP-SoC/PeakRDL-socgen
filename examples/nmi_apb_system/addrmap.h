#ifndef __ADDRMAP__H_
#define __ADDRMAP__H_

#include <cstdint>
#include <string>
#include <vector>
#include <iostream>

struct addrmap{
    uint32_t base;
    uint32_t size;
    uint32_t id;
    std::string path;

    addrmap(uint32_t b, uint32_t s, uint32_t i, std::string p):
        base(b),
        size(s),
        id(i),
        path(p)
    {
    }

    void print(){
        std::cout << "Addrmap: " << path << "\n"
            << " Range: 0x" << std::hex << base << " - 0x" << std::hex << base+size << "\n"
            << " Size: " <<  size << "\n"
            << " ID: " <<  id << "\n";
    }
};


std::vector<addrmap> get_addrmaps();


#endif
