#pragma once

#include <mincostflow/shortestpath.hpp>
    
namespace ln
{
    
    template<typename T>
    class maxflow_base : public digraph_types
    {
        public:
        using value_type = T;    
        static constexpr value_type INFINITY = std::numeric_limits<value_type>::max();
        
        template<typename graph_t>
        value_type flow_at(
            const graph_t& g,
            const arc_pos_t e,
            const std::vector<value_type>& capacity)
        {
            auto e2 = g.arc_dual(e);
            return capacity.at(e2.x);
        }
    };

    template<typename T, typename path_solver_type>
    class maxflow_augmenting_path : public maxflow_base<T>
    {
        public:
        using base_type = maxflow_base<T>;
        using value_type = typename base_type::value_type;    
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        
        
        template<typename graph_t, typename condition_t>
        value_type solve(
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            std::vector<value_type>& capacity,
            condition_t valid_arc)
        {
            value_type sent=0;
            path_solver_type path_solver;
            
            while(1)
            {
                bool found = path_solver.solve(
                    g,
                    Source,Dest,
                    [valid_arc,&capacity](arc_pos_t e)
                    {
                        return capacity.at(e)>0 && valid_arc(e);
                    });
                
                
                if(!found)
                    break;
                
                auto path = path_solver.get_path(g,Dest);
                
                value_type k = INFINITY;
                for(auto e : path)
                {
                    k = std::min(k,capacity.at(e));
                }
                
                for(auto e: path)
                {
                    capacity.at(e) -= k;
                    capacity.at(g.arc_dual(e)) += k;
                } 
                
                sent += k;
            }
            return sent;
        }
        
        maxflow_augmenting_path()
        {}
    };
   
    template<typename T, typename path_solver_type>
    class maxflow_scaling : public maxflow_base<T>
    {
        public:
        using base_type = maxflow_base<T>;
        using value_type = typename base_type::value_type;    
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        template<typename graph_t, typename condition_t>
        value_type solve(
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            std::vector<value_type>& residual_cap,
            condition_t valid_arc)
        // augmenting path
        {
            value_type sent=0;
            path_solver_type search_algo;
            
            value_type cap_flow = 1;
            for(auto e : g.out_arcs(Source))
                cap_flow = std::max(cap_flow,residual_cap.at(e));
            
            cap_flow = lower_bound_power2(cap_flow);
            
            // int cycle=0;
            for(;cap_flow>0;)
            {
                // cycle++;
                // std::cerr << "augmenting path cycle: " << cycle << '\n';
                // std::cerr << "flow sent: " << sent << '\n';
                // std::cerr << "cap flow: " << cap_flow << '\n';
            
                bool found = search_algo.solve(
                    g,
                    Source,Dest,
                    // edge is valid if
                    [this,valid_arc,cap_flow,&residual_cap](arc_pos_t e)
                    {
                        return residual_cap.at(e)>=cap_flow && valid_arc(e);
                    });
                
                if(! found)
                {
                    cap_flow/=2;
                    // std::cerr << "path not found!\n";
                    search_algo.reset();
                    continue;
                }
                
                auto path = search_algo.get_path(g,Dest);
                
                // std::cerr << "path found!\n";
                
                for(auto e: path)
                {
                    residual_cap[e] -= cap_flow;
                    residual_cap[g.arc_dual(e)] += cap_flow;
                } 
                
                sent += cap_flow;
            }
            return sent;
        }
        
        maxflow_scaling()
        {}
    };
    
    
    template<typename T>
    class maxflow_preflow : public maxflow_base<T>, public distance_structure<int>
    {
        public:
        using base_type = maxflow_base<T>;
        using value_type = typename base_type::value_type;    
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        static constexpr auto flow_INFINITY = base_type::INFINITY;
        static constexpr auto dist_INFINITY = distance_structure<int>::INFINITY;
        
        std::vector<T> excess;
        
        template<typename graph_t, typename condition_t>
        void initialize_distance(
            const graph_t& g,
            const node_pos_t Dest,
            condition_t valid_arc)
        {
            distance_structure<int>::init(g);
            
            distance.at(Dest)=0;
            
            std::queue<node_pos_t> q;
            q.push(Dest);
            
            while(!q.empty())
            {
                auto n = q.front();
                q.pop();
                
                for(auto e: g.in_arcs(n))
                if( valid_arc(e) ) 
                {
                    // assert b==n
                    auto [a,b] = g.arc_ends(e);
                    int dnew = distance[b] + 1;
                    
                    if(distance[a]==dist_INFINITY)
                    {
                        distance[a] = dnew;
                        q.push(a);
                    }
                }
            }
        }
        public:
        
        template<typename graph_t, typename condition_t>
        value_type solve(
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            std::vector<value_type>& residual_cap,
            condition_t valid_arc)
        {
            excess.resize(g.max_num_nodes());
            std::fill(excess.begin(),excess.end(),0);
            
            initialize_distance(g,Dest,valid_arc);
            std::queue<node_pos_t> q;
            
            auto push = [&](arc_pos_t e)
            {
                auto [a,b] = g.arc_ends(e);
                const auto delta = std::min(excess[a],residual_cap.at(e));
                residual_cap.at(e) -= delta;
                residual_cap.at(g.arc_dual(e)) += delta;
                
                assert(delta>=0);
                
                excess.at(a) -= delta;
                excess.at(b) += delta;
                
                if(delta>0 && excess.at(b)==delta)
                    q.push(b);
            };
            
            auto relabel = [&](node_pos_t v)
            {
                int hmin = dist_INFINITY;
                for(auto e : g.out_arcs(v))
                    if(valid_arc(e) && residual_cap.at(e)>0)
                        hmin = std::min(hmin,distance.at(g.arc_ends(e).second));
                if(hmin<dist_INFINITY)    
                    distance.at(v) = hmin+1;
            };
            
            auto discharge = [&](node_pos_t a)
            {
                while(true)
                {
                    for(auto e : g.out_arcs(a))
                        if(valid_arc(e) && residual_cap.at(e)>0)
                        {
                            auto b = g.arc_ends(e).second;
                            if(distance[a]== distance[b]+1)
                                push(e);
                        }
                    
                    if(excess.at(a)==0)
                        break;
                    
                    relabel(a);
                }
            };
            
            excess.at(Source) = flow_INFINITY;
            distance.at(Source) = g.num_nodes();
            
            for(auto e : g.out_arcs(Source))
                if(valid_arc(e))
                    push(e);
            
            while(!q.empty())
            {
                auto node = q.front();
                q.pop();
                
                if(node!=Dest && node!=Source)
                    discharge(node);
            }
            return excess.at(Dest);
        }
        maxflow_preflow()
        {}
        
    };
}
