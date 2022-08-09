#pragma once

#include <cstdint>
#include <cstddef>
#include <vector>
#include <set>
#include <stdexcept>
#include <cassert>
#include <limits>
    
namespace ln
{
    template<typename index_t, typename data_t>
    class vectorized_map
    /*
        a map-like data structure
        that holds elements in a vector, hence access is O(1)
        new elements are added to the smallest available slot and the key is returned,
        we don't choose the key associated to an element, but once the key is set it will
        remain valid until the element is removed.
        iterators point to key values, not data,
        though data can be accessed through the key
    */
    {
        using size_t = std::size_t;
        
        static constexpr index_t MAX_IDX = std::numeric_limits<index_t>::max();
        std::vector< bool > valid_flag;
        std::vector< data_t > data;
        std::set< index_t > free_slots;
        
        void check_invariants()const
        {
            assert(valid_flag.size()==data.size());
        }
        
        void free_space()
        {
            while(!data.empty() && !valid_flag.back())
            // eliminate unused elements from the back of the buffer
            {
                auto ptr = index_t{data.size()-1};
                assert(free_slots.find(ptr)!=free_slots.end());
                
                free_slots.erase(ptr);
                valid_flag.pop_back();
                data.pop_back();
            }
            check_invariants();
        }
        
        class base_iterator
        {
            protected:
            const vectorized_map& const_ref;
            index_t pos;
            
            void check_invariants()const
            {
                bool is_valid = const_ref.is_valid(pos);
                bool is_infty = size_t(pos)==MAX_IDX;
                
                assert(is_valid ^ is_infty);
            }
            
            
            void next_valid()
            {
                while(size_t(pos)<const_ref.capacity() && !const_ref.is_valid(pos))
                {
                    pos++;
                }
                if(size_t(pos)>=const_ref.capacity())
                    pos = index_t{MAX_IDX};
            }
            
            public:
            base_iterator(const vectorized_map& c, index_t x):
                const_ref{c},
                pos{x}
            {}
        
        };
        
        class iterator : public base_iterator
        {
            using base_iterator::pos;
            using base_iterator::next_valid;
            using base_iterator::check_invariants;
            using base_iterator::const_ref;
            
            public:
            iterator(vectorized_map& c, index_t x):
                base_iterator{c}
            {
                next_valid();
                check_invariants();
            }
            
            bool operator==(const iterator& that)const
            {
                return pos == that.pos;
            }
            bool operator != (const iterator& that)const
            {
                return !(pos==that.pos);
            }
            index_t operator * ()const
            {
                return pos;
            }
            
            iterator& operator++()
            {
                if(!const_ref.is_valid(pos)) 
                    return *this;
                ++pos;
                next_valid();
                check_invariants();
                return *this;
            }
        };
        class const_iterator : public base_iterator
        {
            using base_iterator::pos;
            using base_iterator::next_valid;
            using base_iterator::check_invariants;
            using base_iterator::const_ref;
            
            public:
            
            const_iterator(const vectorized_map& c, index_t x):
                base_iterator{c,x}
            {
                next_valid();
                check_invariants();
            }
            
            bool operator==(const const_iterator& that)const
            {
                return pos == that.pos;
            }
            bool operator != (const const_iterator& that)const
            {
                return !(pos==that.pos);
            }
            index_t operator * ()const
            {
                return pos;
            }
            
            const_iterator& operator++()
            {
                if(!const_ref.is_valid(pos)) 
                    return *this;
                ++pos;
                next_valid();
                check_invariants();
                return *this;
            }
        };
        
        public:
        bool is_valid(index_t pos)const
        {
            return size_t(pos)<data.size() && valid_flag.at(pos);
        }
        auto begin()
        {
            return iterator(*this,index_t{0});
        }
        auto begin()const
        {
            return const_iterator(*this,index_t{0});
        }
        auto cbegin()const
        {
            return const_iterator(*this,index_t{0});
        }
        auto end()
        {
            return iterator(*this,MAX_IDX);
        }
        auto end()const
        {
            return const_iterator(*this,MAX_IDX);
        }
        auto cend()const
        {
            return iterator(*this,MAX_IDX);
        }
        
        const data_t& operator[](index_t x)const
        {
            return data[x];
        }
        data_t& operator[](index_t x)
        {
            return data[x];
        }
        const data_t& at(index_t x)const
        {
            if(!is_valid(x))
                std::runtime_error(
                    "vectorized_map::at failed with x="
                    +std::to_string(size_t(x)));
            return data.at(x);
        }
        data_t& at(index_t x)
        {
            if(!is_valid(x))
                std::runtime_error(
                    "vectorized_map::at failed with x="
                    +std::to_string(size_t(x)));
            return data.at(x);
        }
        
        size_t size()const
        {
            return data.size()-free_slots.size();
        }
        size_t capacity()const
        {
            return data.size();
        }
        
        void erase(index_t pos)
        {
            if(! is_valid(pos))
                return;
            
            valid_flag.at(pos)=false;
            free_slots.insert(pos);
            
            free_space();
            check_invariants();
        }
        index_t insert(data_t d)
        {
            index_t x{};
            if(!free_slots.empty())
            // take an element from a free slot
            {
                x = *free_slots.begin();
                free_slots.erase(x);
                valid_flag.at(x) = true;
                data.at(x) = d;
            }else
            // take an element from the back of the buffer
            {
                x=index_t{data.size()};
                data.push_back(d);
                valid_flag.emplace_back(true);
            }
            check_invariants();
            return x;
        }
    };
}
