#pragma once

#include <mincostflow/graph.hpp>

#include <iostream>
#include <set>
#include <algorithm>
#include <queue>
#include <vector>
#include <cassert>


namespace ln
{
    inline long long int lower_bound_power2(long long int n)
    {
        if(n<=2) return n;
        while(n != (n & -n))
            n -= (n & -n);
        return n;
    }
    
    
    class parent_structure : public digraph_types
    {
        public:
        std::vector<arc_pos_t> parent;
       
        bool has_parent(node_pos_t x)const
        {
            return parent.at(x)!=arc_pos_t{NONE};
        }
        bool is_reacheable(node_pos_t x)const
        {
            return has_parent(x);
        }
        
        template<typename graph_t>
        void init(const graph_t& g)
        {
            parent.resize(g.max_num_nodes());
            std::fill(parent.begin(),parent.end(),arc_pos_t{NONE});
        }
        
        
        template<typename graph_t>
        auto get_path(const graph_t& g,node_pos_t last)const
        {
            std::vector<arc_pos_t> path;
            while(1)
            {
                auto e = parent.at(last);
                if(!g.is_valid(e))
                    break;
                
                path.push_back(e);
                auto [a,b] = g.arc_ends(e);
                last = a;
                
            }
            return path;
        }
    };
    
    template<typename T>
    class distance_structure
    {
        public:
        using value_type = T;
        static constexpr value_type INFINITY = std::numeric_limits<value_type>::max();
        std::vector<value_type> distance;
        
        template<typename graph_t>
        void init(const graph_t& g)
        {
            distance.resize(g.max_num_nodes());
            std::fill(distance.begin(),distance.end(),INFINITY);
        }
    };
    
    
    class pathSearch_BFS : public parent_structure, public distance_structure<int>
    /*
        Represents: weigthless path using BFS
        Invariant:
        
        User interface: 
        Complexity: |E|+|V|
    */
    {
        public:
        using value_type = int;
        using parent_structure::parent;
        using parent_structure::init;
        using distance_structure<value_type>::distance;
        using distance_structure<value_type>::init;
        using distance_structure<value_type>::INFINITY;
        
        pathSearch_BFS()
        {
        }
        
        void reset()
        {}
        
        template<typename graph_t, typename condition_t>
        bool solve (
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            condition_t valid_arc)
        // each call resets the state of the tree and distances
        // O(|E|+|V|)
        {
            bool found = false;
            
            if(!g.is_valid(Source))
                throw std::runtime_error(
                    "pathSearch_BFS::solve source node is not valid");
            
            if(!g.is_valid(Dest))
                throw std::runtime_error(
                    "pathSearch_BFS::solve destination node is not valid");
            
            parent_structure::init(g);
            distance_structure::init(g);
            
            distance.at(Source) = 0;
            
            std::queue<node_pos_t> q;
            q.push(Source);
            
            while(!q.empty())
            {
                auto node = q.front();
                q.pop();
                
                if(node==Dest)
                {
                    found = true;
                    break;
                }
                for(auto e: g.out_arcs(node))
                if( valid_arc(e) ) 
                {
                    auto [a,b] = g.arc_ends(e);
                    
                    if(distance.at(b)==INFINITY)
                    {
                        distance.at(b) = distance.at(a)+1;
                        parent.at(b) = e;
                        q.push(b);
                    }
                }
            }
            return found;
        }
    };
    
    class pathSearch_labeling : public parent_structure, 
                                public distance_structure<unsigned int>
    /*
        Represents: shortest path with labeling
        Invariant:
        
        User interface: 
        Complexity:
    */
    {
        public:
        using value_type = distance_structure::value_type;
        using parent_structure::parent;
        using parent_structure::init;
        using distance_structure<value_type>::distance;
        using distance_structure<value_type>::init;
        using distance_structure<value_type>::INFINITY;
        
        node_pos_t last_source{NONE},last_dest{NONE};
        std::vector<int> dist_freq;
        
        template<typename graph_t, typename condition_t>
        void initialize (
            const graph_t &g,
            condition_t valid_arc)
        {
            parent_structure::init(g);
            distance_structure::init(g);
            
            dist_freq.resize(g.num_nodes()+1);
            std::fill(dist_freq.begin(),dist_freq.end(),0);
            
            std::queue<node_pos_t> q;
            distance.at(last_dest)=0;
            
            // TODO: write a general purpose BFS label solver
            q.push(last_dest);
            
            while(!q.empty())
            {
                auto n = q.front();
                q.pop();
                
                for(auto e: g.in_arcs(n))
                if( valid_arc(e) ) 
                {
                    auto [a,b] = g.arc_ends(e);
                    value_type dnew = distance[b] + 1;
                    
                    if(distance[a]==INFINITY)
                    {
                        distance[a] = dnew;
                        dist_freq.at(dnew)++;
                        q.push(a);
                    }
                }
            }
        }
        
        
        public:
        
        pathSearch_labeling()
        {}
        
        
        void reset()
        {
            last_source = last_dest = node_pos_t{NONE};
        }
        template<typename graph_t, typename condition_t>
        bool solve (
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            condition_t valid_arc)
        {
            if(last_source!=Source || last_dest!=Dest)
            {
                last_source = Source;
                last_dest = Dest;
                initialize(g,valid_arc);
            }
            
            parent_structure::init(g);
            
            
            for(auto current = Source;
                distance.at(Source)<g.num_nodes() && current!=Dest;)
            {
               // advance
               bool found_next=false;
               for(auto e : g.out_arcs(current))
               {
                    auto [x,next] = g.arc_ends(e);
                    if(valid_arc(e) && distance.at(current)==distance.at(next)+1)
                    {
                        found_next = true;
                        parent.at(next) = e;
                        current = next;
                        break;
                    }
               }
               if(found_next) continue; // advance success
               
               // relabel
               value_type min_dist = g.num_nodes()+10;
               for(auto e : g.out_arcs(current))
               {
                    auto [x,next] = g.arc_ends(e);
                    if(valid_arc(e))
                    {
                        min_dist= std::min(min_dist,distance.at(next));
                    }
               }
               {
                    const value_type new_dist = min_dist+1;
                    const value_type old_dist = distance.at(current);
                    distance.at(current) = new_dist;
                    if(new_dist<dist_freq.size())
                        dist_freq.at(new_dist)++;
                    dist_freq.at(old_dist)--;
                    if(dist_freq.at(old_dist)==0)
                        break;
               }
               
               // retreat
               if(has_parent(current))
               {
                    auto e = parent.at(current);
                    current = g.arc_ends(e).first;
               }
            }
            return has_parent(Dest);
        }
        // TODO: optimize page 219 Ahuja
    };
    
    template<typename T>
    class shortestPath_FIFO : public parent_structure, public distance_structure<T>
    /*
        Represents: shortest path label-correcting FIFO
        Invariant:
        
        User interface: 
        Complexity: pseudo-polynomial
    */
    {
        public:
        using value_type = T;
        using parent_structure::parent;
        using parent_structure::init;
        using distance_structure<value_type>::distance;
        using distance_structure<value_type>::init;
        using distance_structure<value_type>::INFINITY;
        
        shortestPath_FIFO()
        {}
        
        template<typename graph_t, typename condition_t>
        void solve(
            const graph_t& g,
            const node_pos_t Source,
            const std::vector<value_type>& weight,
            condition_t valid_arc)
        // shortest path FIFO
        // each call resets the state of the tree and distances
        // O( pseudo-polynomial )
        {
            parent_structure::init(g);
            distance_structure<value_type>::init(g);
            
            if(!g.is_valid(Source))
                throw std::runtime_error(
                    "shortestPath_FIFO::solve source node is not valid");
            
            if(weight.size()<g.max_num_arcs())
                throw std::runtime_error(
                    "shortestPath_FIFO::solve weight does not map arc property");
            
            std::queue<node_pos_t> q;
            q.push(Source);
            distance.at(Source)=0;
            
            while(!q.empty())
            {
                auto node = q.front();
                q.pop();
                
                for(auto e: g.out_arcs(node))
                if( valid_arc(e) ) 
                {
                    auto [a,b] = g.arc_ends(e);
                    const value_type dnew = distance.at(a)+weight.at(e);
                    
                    if(distance.at(b)>dnew)
                    {
                        distance.at(b) = dnew;
                        parent.at(b) = e;
                        q.push(b);
                    }
                }
            }
        }
    };
    
    template<typename T>
    class shortestPath_BellmanFord : public parent_structure, public distance_structure<T>
    /*
        Represents: shortest path using Bellman-Ford
        Invariant:
        
        User interface: 
        Complexity: |V| |E|
    */
    {
        public:
        using value_type = T;
        using parent_structure::parent;
        using parent_structure::init;
        using distance_structure<value_type>::distance;
        using distance_structure<value_type>::init;
        using distance_structure<value_type>::INFINITY;
        
        shortestPath_BellmanFord()
        {}
        
        template<typename graph_t, typename condition_t>
        void solve (
            const graph_t& g,
            const node_pos_t Source,
            const std::vector<value_type>& weight,
            condition_t valid_arc)
        // shortest path Bellman-Ford
        // each call resets the state of the tree and distances
        // O(|V||E|)
        {
            parent_structure::init(g);
            distance_structure<value_type>::init(g);
            
            if(!g.is_valid(Source))
                throw std::runtime_error(
                    "shortestPath_BellmanFord::solve source node is not valid");
            
            if(weight.size()<g.max_num_arcs())
                throw std::runtime_error(
                    "shortestPath_BellmanFord::solve weight does not map arc property");
            
            distance.at(Source) = 0;
            
            // TODO: use here the right number of nodes
            for(auto i=0UL;i<g.num_nodes();++i)
            {
                bool updates = false;
                for(auto e: g.arcs())
                {
                    if(valid_arc(e))
                    {
                        const auto [a,b] = g.arc_ends(e);
                        if(distance.at(a)==INFINITY)
                            continue;
                        
                        const value_type dnew = distance[a]+weight.at(e);
                        if(distance.at(b)>dnew)
                        {
                            distance[b]=dnew;
                            parent.at(b) = e;
                            updates = true;
                        }
                    }
                }
                if(! updates)
                    break;
            }
            // TODO: check for negative cycles
        }
    };
    
    template<typename T>
    class shortestPath_Dijkstra : public parent_structure, public distance_structure<T>
    /*
        Represents: shortest path with weights using Dijkstra
        Invariant:
        
        User interface: 
        Complexity: |E| + |V| log |V|
    */
    {
        public:
        using value_type = T;
        using parent_structure::parent;
        using parent_structure::init;
        using distance_structure<value_type>::distance;
        using distance_structure<value_type>::init;
        using distance_structure<value_type>::INFINITY;
        
        shortestPath_Dijkstra()
        {}
        
        template<typename graph_t, typename condition_t>
        void solve (
            const graph_t& g,
            const node_pos_t Source,
            const std::vector<value_type>& weight,
            condition_t valid_arc)
        // Dijkstra algorithm 
        // precondition: doesnt work with negative weights!
        // O( |E|+|V| log |V| )
        {
            parent_structure::init(g);
            distance_structure<value_type>::init(g);
            
            if(!g.is_valid(Source))
                throw std::runtime_error(
                    "shortestPath_Dijkstra::solve source node is not valid");
            
            if(weight.size()<g.max_num_arcs())
                throw std::runtime_error(
                    "shortestPath_Dijkstra::solve weight does not map arc property");
            
            std::vector<bool> visited(g.max_num_nodes(),false);
            
            distance.at(Source) = 0;
            std::priority_queue< 
                std::pair<value_type,node_pos_t>, 
                std::vector< std::pair<value_type,node_pos_t> >, 
                std::greater<std::pair<value_type,node_pos_t> > 
                > q;
            q.push( {0,Source} );
            
            while(!q.empty())
            {
                const auto [dist,node] = q.top();
                q.pop();
                
                if(visited.at(node))
                    continue;
                
                visited[node]=true;
                
                for(auto e: g.out_arcs(node))
                if( valid_arc(e) ) 
                {
                    auto [a,b] = g.arc_ends(e);
                    
                    if(weight.at(e)<0)
                        throw std::runtime_error(
                            "shortestPath_Dijkstra::solve found a negative edge");
                    
                    value_type dnew = dist + weight.at(e);
                    if(distance.at(b)>dnew)
                    {
                        distance[b] = dnew;
                        parent[b] = e;
                        q.push({dnew,b});
                    }
                }
            }
        }
    };
}
