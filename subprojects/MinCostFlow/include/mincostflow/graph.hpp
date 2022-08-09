#pragma once

#include <mincostflow/vectorized_map.hpp>

#include <stdexcept>
#include <limits>
#include <cassert>
#include <cstdint>
#include <vector>
#include <set>
#include <unordered_map>
#include <algorithm>


namespace ln
{   

    class digraph_types
    {
        public:
        
        // a lot more efficient if we can internally identify arcs and nodes by their unique
        // position in the buffer array
        typedef std::size_t pos_type;
        static constexpr pos_type NONE = std::numeric_limits<pos_type>::max();
        
        struct node_pos_t
        {
            pos_type x{NONE};
            bool operator<(const node_pos_t& that)const
            {
                return x < that.x;
            }
            bool operator==(const node_pos_t& that)const
            {
                return x==that.x;
            }
            
            operator pos_type() const
            {
                return x;
            }
            node_pos_t& operator++()
            {
                ++x;
                return *this;
            }
            node_pos_t operator++(int)
            {
                ++x;
                return node_pos_t{x-1};
            }
        };
        struct arc_pos_t
        {
            pos_type x{NONE};
            bool operator<(const arc_pos_t& that)const
            {
                return x < that.x;
            }
            bool operator==(const arc_pos_t& that)const
            {
                return x==that.x;
            }
            operator pos_type() const
            {
                return x;
            }
            arc_pos_t& operator++()
            {
                ++x;
                return *this;
            }
            arc_pos_t operator++(int)
            {
                ++x;
                return arc_pos_t{x-1};
            }
        };
        
        struct arc_data_t
        {
            node_pos_t a{NONE},b{NONE};
            arc_pos_t dual{NONE};
        };
        
        struct node_data_t
        {
            std::vector<arc_pos_t> out_arcs,in_arcs;
            
            void rm_arc(arc_pos_t arc)
            {
                auto rm_arc_vec=[arc](std::vector<arc_pos_t>& V)
                {
                    if (auto ptr = std::find(V.begin(),V.end(),arc);
                             ptr!=V.end())
                    {
                        *ptr = V.back();
                        V.pop_back();
                    }
                };
                rm_arc_vec(in_arcs);
                rm_arc_vec(out_arcs);
            }
            void add_in_arc(arc_pos_t arc)
            {
                in_arcs.push_back(arc);
            }
            void add_out_arc(arc_pos_t arc)
            {
                out_arcs.push_back(arc);
            }
        };
    };
    
    
    // TODO: template on custom allocator
    template<typename node_id_t, typename arc_id_t>
    class digraph : public digraph_types
    /*
        Represents: a directed graph with dual arcs to simulate the residual network.
        This data structure represents only the topological information.
        Nodes and arcs have fixed positions.
    */
    /*
        ideally I would like to:
        
        digraph<node_id_t,arc_id_t> g;
        
        g.add_arc(node_a,node_b,arc_ab); // adds also the dual
        
        g::node_id_t n_1 = g.source_node(arc_x); 
        g::node_id_t n_2 = g.dest_node(arc_x); 
        
        g::node_id_t n = g.add_node(node_factory); // generates a new node
        
        
        
        // an optimized interface allows to pass additional structure as arrays
        g.max_nodes(); // size of the node array
        g.max_arcs() ; // size of arc array
        
        for()
    */
    {
        vectorized_map<arc_pos_t,arc_data_t> my_arcs;
        vectorized_map<node_pos_t,node_data_t> my_nodes;
        
        std::unordered_map<arc_id_t,arc_pos_t> arcs_htable;
        std::vector<arc_id_t> arcs_ids;
        std::vector<bool> arcs_ids_flag;
        
        std::unordered_map<node_id_t,node_pos_t> nodes_htable;
        std::vector<node_id_t> nodes_ids;
        std::vector<bool> nodes_ids_flag;
            
        public:
        
        const auto& arcs()const
        {
            return my_arcs;
        }
        const auto& nodes()const
        {
            return my_nodes;
        }
        
        bool is_valid(arc_pos_t arc)const
        {
            return my_arcs.is_valid(arc);
        }
        bool is_valid(node_pos_t node)const
        {
            return my_nodes.is_valid(node);
        }
        bool has_id(node_pos_t node)const
        {
            return nodes_ids_flag.at(node);
        }
        bool has_id(arc_pos_t arc)const
        {
            return arcs_ids_flag.at(arc);
        }
        
        auto arc_ends(arc_pos_t arc)const
        {
            return std::pair<node_pos_t,node_pos_t>{
                my_arcs.at(arc).a,
                my_arcs.at(arc).b
                };
        }
        arc_pos_t arc_dual(arc_pos_t arc)const
        {
            return my_arcs.at(arc).dual;
        }
        
        auto arc_ends_nocheck(arc_pos_t arc)const noexcept
        {
            return std::pair<node_pos_t,node_pos_t>{
                my_arcs[arc].a,
                my_arcs[arc].b
                };
        }
        arc_pos_t arc_dual_nocheck(arc_pos_t arc)const noexcept
        {
            return my_arcs[arc].dual;
        }
        
        void erase(arc_pos_t arc)
        {
            if(! is_valid(arc))
                return;
            
            auto [a,b] = arc_ends(arc);
            
            my_nodes.at(a).rm_arc(arc);
            my_nodes.at(b).rm_arc(arc);
            
            if(has_id(arc))
            {
                auto id = arcs_ids.at(arc);
                arcs_htable.erase(id);
            }
            
            my_arcs.erase(arc);
            arcs_ids.resize(my_arcs.capacity());
            arcs_ids_flag.resize(my_arcs.capacity());
        }
        void erase(node_pos_t node)
        {
            if(! is_valid(node))
                return;
            std::vector<arc_pos_t> ls_arcs;
            std::copy(my_nodes.at(node).in_arcs.begin(),
                      my_nodes.at(node).in_arcs.end(),
                      std::back_inserter(ls_arcs));
            std::copy(my_nodes.at(node).out_arcs.begin(),
                      my_nodes.at(node).out_arcs.end(),
                      std::back_inserter(ls_arcs));
                      
            // first remove all incoming and outgoin arcs
            for(auto arc: ls_arcs)
                erase(arc);
            
            if(has_id(node))
            {
                auto id = nodes_ids.at(node);
                nodes_htable.erase(id);
            }
            my_nodes.erase(node);
            nodes_ids.resize(my_nodes.capacity());
            nodes_ids_flag.resize(my_nodes.capacity());
        }
        node_pos_t new_node()
        {
            node_pos_t node = my_nodes.insert(node_data_t{});
            
            nodes_ids.resize(my_nodes.capacity());
            nodes_ids_flag.resize(my_nodes.capacity());
            
            nodes_ids_flag.at(node)=false;
            
            return node;
        }
        
        const auto& out_arcs(node_pos_t node)const
        {
            if(!is_valid(node))
                throw std::runtime_error(
                    "digraph::out_arcs invalid node");
            return my_nodes.at(node).out_arcs;
        }
        const auto& in_arcs(node_pos_t node)const
        {
            if(!is_valid(node))
                throw std::runtime_error(
                    "digraph::in_arcs invalid node");
            return my_nodes.at(node).in_arcs;
        }
        
        arc_pos_t new_arc(node_pos_t a, node_pos_t b)
        {
            if(!is_valid(a) || !is_valid(b))
                throw std::runtime_error("digraph::new_arc add a new arc with invalid end nodes");
            
            arc_pos_t arc = my_arcs.insert(arc_data_t{a,b,NONE});
            arcs_ids.resize(my_arcs.capacity());
            arcs_ids_flag.resize(my_arcs.capacity());
            
            arcs_ids_flag.at(arc)=false;
            
            my_nodes.at(a).add_out_arc(arc); 
            my_nodes.at(b).add_in_arc(arc); 
            return arc;
        }
        void set_dual(arc_pos_t arc1, arc_pos_t arc2)
        {
            if(!is_valid(arc1) || !is_valid(arc2))
                throw std::runtime_error("digraph::set_dual invalid arcs");
                
            my_arcs.at(arc1).dual = arc2;
            my_arcs.at(arc2).dual = arc1;
        }
        
        auto max_num_arcs()const
        {
            return my_arcs.capacity();
        }
        auto num_arcs()const
        {
            return my_arcs.size();
        }
        auto max_num_nodes()const
        {
            return my_nodes.capacity();
        }
        auto num_nodes()const
        {
            return my_nodes.size();
        }
        
        // translation 
        node_id_t get_node_id(node_pos_t node)const
        {
            if(!is_valid(node))
                throw std::runtime_error("digraph::get_node_id invalid node");
            if(!has_id(node))
                throw std::runtime_error("digraph::get_node_id node without id");
            return nodes_ids.at(node);
        }
        arc_id_t get_arc_id(arc_pos_t arc)const
        {
            if(!is_valid(arc))
                throw std::runtime_error("digraph::get_arc_id invalid arc");
            if(!has_id(arc))
                throw std::runtime_error("digraph::get_arc_id arc without id");
            return arcs_ids.at(arc);
        }
        node_pos_t get_node(node_id_t id)const
        {
            node_pos_t node{NONE};
            if(auto ptr = nodes_htable.find(id);
               ptr != nodes_htable.end())
            {
                node = ptr->second;
            }
            return node;
        }
        arc_pos_t get_arc(arc_id_t id)const
        {
            arc_pos_t arc{NONE};
            if(auto ptr = arcs_htable.find(id);
               ptr != arcs_htable.end())
            {
                arc = ptr->second;
            }
            return arc;
        }
        node_pos_t add_node(node_id_t id)
        {
            auto node = get_node(id);
            if(!is_valid(node))
            {
                node = new_node();
                nodes_ids.at(node) = id;
                nodes_ids_flag.at(node) = true;
                nodes_htable[id] = node;
            }
            return node;
        }
        std::pair<arc_pos_t,arc_pos_t> add_arc(node_id_t a, node_id_t b, arc_id_t id)
        {
            auto n_a = add_node(a);
            auto n_b = add_node(b);
            
            if(auto arc = get_arc(id); is_valid(arc))
                throw std::runtime_error("digraph::add_arc arc id already exists");
            
            auto arc1 = new_arc(n_a,n_b);
            auto arc2 = new_arc(n_b,n_a);
            set_dual(arc1,arc2);
            
            arcs_ids.at(arc1) = id;
            arcs_ids_flag.at(arc1) = true;
            arcs_htable[id] = arc1;
            
            return {arc1,arc2};
        }
        void remove_node(node_id_t id)
        {
            auto node = get_node(id);
            if(!is_valid(node))
                return;
            nodes_htable.erase(id);
            erase(node);
        }
        void remove_arc(arc_id_t id)
        {
            auto arc = get_arc(id);
            if(!is_valid(arc))
                return;
            arcs_htable.erase(id);
            
            auto arc2 = arc_dual(arc);
            erase(arc);
            erase(arc2);
        }
        
        digraph()
        {}
    };
}
