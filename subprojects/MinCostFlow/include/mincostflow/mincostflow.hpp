#pragma once

#include <mincostflow/maxflow.hpp>
#include <mincostflow/scope_guard.hpp>

namespace ln
{
    template<typename T, typename path_optimizer_type>
    class mincostflow_EdmondsKarp : public maxflow_base<T>
    {
        public:
        using base_type = maxflow_base<T>;
        using value_type = typename base_type::value_type;    
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        template<typename graph_t>
        value_type solve(
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            const std::vector<value_type>& weight,
                  std::vector<value_type>& residual_cap
            )
        // augmenting path
        {   
            value_type sent =0 ;
            path_optimizer_type path_opt;
            
            while(true)
            {
                path_opt.solve(
                    g,
                    Source,
                    weight,
                    // edge is valid if
                    [&residual_cap](arc_pos_t e){
                        return residual_cap.at(e)>0;
                    });
                
                if(! path_opt.is_reacheable(Dest))
                    break;
                
                auto path = path_opt.get_path(g,Dest);
                
                value_type k = INFINITY;
                for(auto e : path)
                {
                    k = std::min(k,residual_cap.at(e));
                }
                
                for(auto e: path)
                {
                    residual_cap[e] -= k;
                    residual_cap[g.arc_dual(e)] += k;
                } 
                
                sent += k;
            }
            return sent;
        }
        
        mincostflow_EdmondsKarp()
        {}
    };
    
    
    template<typename path_optimizer_type, typename maxflow_type>
    class mincostflow_PrimalDual : public maxflow_type
    {
        public:
        using base_type = maxflow_type;
        using value_type = typename base_type::value_type;    
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        
        template<typename graph_t>
        value_type solve(
            const graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            const std::vector<value_type>& weight,
                  std::vector<value_type>& residual_cap
            )
        {   
            std::vector<value_type> reduced_weight = weight;
            
            value_type sent =0 ;
            path_optimizer_type path_opt;
            
            while(true)
            {
                path_opt.solve(
                    g,
                    Source,
                    reduced_weight,
                    // edge is valid if
                    [&residual_cap](arc_pos_t e) -> bool
                    {
                        return residual_cap.at(e)>0;
                    });
                    
                if(! path_opt.is_reacheable(Dest))
                    break;
                    
                const auto& distance{path_opt.distance};
                
                for(auto e : g.arcs())
                {
                
                    auto [a,b] = g.arc_ends(e);
                    if(distance[a]<INFINITY && distance[b]<INFINITY)
                    {
                        reduced_weight[e]       += distance[a]-distance[b];
                    }
                }
                
                
                auto F = base_type::solve(
                    g,
                    Source,Dest,
                    residual_cap,
                    // admissibility
                    [&reduced_weight](arc_pos_t e)->bool
                    {
                        return reduced_weight[e]==0;
                    });
                
                sent += F;
            }
            return sent;
        }
        
        mincostflow_PrimalDual()
        {}
    };
    
    template<typename path_optimizer_type, typename maxflow_type>
    class mincostflow_capacityScaling : public maxflow_type
    {
        public:
        using base_type = maxflow_type;
        using value_type = typename base_type::value_type;
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t  = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        template<typename graph_t>
        value_type solve(
            graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            const std::vector<value_type>& weight,
                  std::vector<value_type>& residual_cap)
        {
        
            std::vector<value_type> reduced_weight = weight;
            value_type maxflow{0};
            
            // find the max-flow-anycost
            maxflow = maxflow_type::solve(
                g,Source,Dest,
                residual_cap,
                [](arc_pos_t)->bool{return true;});
            
            value_type cap_flow = lower_bound_power2(maxflow);
            
            std::vector<value_type> excess(g.max_num_nodes(),0);
            
            std::vector<value_type> weight_ex = weight;
            
            auto update_reduced_costs = 
                [&](const std::vector<value_type>& potential)
            {
                for(auto e : g.arcs())
                {
                    auto [src,dst] = g.arc_ends(e);
                    auto p_src = potential.at(src), p_dst = potential.at(dst);
                    
                    p_src = p_src == INFINITY ? 0 : p_src;
                    p_dst = p_dst == INFINITY ? 0 : p_dst;
                    
                    weight_ex.at(e) +=  p_src - p_dst;
                }
            };
            
            auto push_flow = 
                [&](arc_pos_t e,value_type delta)
            {
                    // std::cerr << " push flow at " << e << " delta = " << delta << "\n";
                    auto [src,dst] = g.arc_ends(e);
                    
                    residual_cap[e]-=delta;
                    residual_cap[g.arc_dual(e)]+=delta;
                    
                    excess.at(src) -= delta;
                    excess.at(dst) += delta;
                    
                    // std::cerr << "push " << delta << " over " << e << '\n';
            };
            
            // auto report = 
            // [&]()
            // {
            //     std::cerr << "residual cap + mod. costs\n";
            //     for(auto e : g.arcs())
            //     {
            //         std::cerr << " " << e << " -> " << residual_cap[e] << " " << weight_ex[e] << "\n";
            //     }
            //     std::cerr << "potential + excess\n";
            //     for(auto v : g.nodes())
            //     {
            //         std::cerr << " " << v << " -> " << excess[v] << "\n";
            //     }
            // };
            // 
            // std::cerr << " maxflow = " << maxflow << "\n";
            
            // int cycle=0;
            for(;cap_flow>0;cap_flow/=2)
            {
                // cycle++;
                // std::cerr << "cycle " << cycle << " cap_flow = " << cap_flow << '\n';
                // report();
                
                // saturate edges with negative cost
                for(auto e : g.arcs()) 
                while(residual_cap.at(e)>=cap_flow && weight_ex.at(e)<0)
                {
                    push_flow(e,cap_flow);
                }
                
                path_optimizer_type path_opt;
                
                // build S and T
                std::set<node_pos_t> Sset,Tset;
                for(auto v : g.nodes())
                {
                    if(excess.at(v)>=cap_flow)
                        Sset.insert(v);
                    if(excess.at(v)<=-cap_flow)
                        Tset.insert(v);
                }
                
                const auto multi_source_node = g.new_node();
                excess.resize(g.max_num_nodes());
                excess.at(multi_source_node) = 0;
                const Scope_guard rm_node = [&](){ g.erase(multi_source_node);};
                
                
                
                for(auto v : Sset)
                {
                    auto arc1 = g.new_arc(multi_source_node,v);
                    auto arc2 = g.new_arc(v,multi_source_node);
                    
                    g.set_dual(arc1,arc2);
                    
                    weight_ex.resize(g.max_num_arcs());
                    residual_cap.resize(g.max_num_arcs());
                    
                    weight_ex.at(arc1) = 0;
                    residual_cap.at(arc1) = excess.at(v);
                    
                    weight_ex.at(arc2) = 0;
                    residual_cap.at(arc2) = 0;
                    
                    excess.at(multi_source_node) += excess.at(v);
                    excess.at(v) = 0;
                }
                
                const Scope_guard restore_excess = [&]()
                {
                    for(auto e : g.out_arcs(multi_source_node))
                    {
                        auto [src,dst] = g.arc_ends(e);
                        excess.at(dst) = residual_cap.at(e);
                    }
                };
                
                while(!Sset.empty() && !Tset.empty())
                { 
                    path_opt.solve(
                        g, multi_source_node,
                        weight_ex,
                        [cap_flow,&residual_cap](arc_pos_t e)->bool
                        {
                            return residual_cap.at(e)>=cap_flow;
                        }
                    );
                    
                    const auto& distance{path_opt.distance};
                    
                    auto it = std::find_if(Tset.begin(),Tset.end(),
                        [&](node_pos_t v)->bool {
                            return distance.at(v)<INFINITY;
                        });
                    
                    if(it==Tset.end())
                        break;
                    
                    auto dst = *it;
                    
                    
                    // std::cerr << " vertex distance to pivot\n";
                    // for(int v=0;v<Graph.n_vertex();++v)
                    // {
                    //     std::cerr << " " <<v <<" -> " << distance[v]<<"\n";
                    // }
                    
                    update_reduced_costs(distance);
                    
                    auto path = path_opt.get_path(g,dst);
                    for(auto e: path)
                    {
                        // auto [src,dst] = g.arc_ends(e);
                        push_flow(e,cap_flow);
                    }
                    
                    if(excess.at(dst)>-cap_flow)
                        Tset.erase(dst);
                }
            }
            
            return maxflow;
        }
        
        public:
        mincostflow_capacityScaling()
        {}
    };
    
    template<typename maxflow_type>
    class mincostflow_costScaling : public maxflow_type
    {
        public:
        using base_type = maxflow_type;
        using value_type = typename base_type::value_type;
        using node_pos_t = typename base_type::node_pos_t;
        using arc_pos_t  = typename base_type::arc_pos_t;
        using base_type::flow_at;
        using base_type::INFINITY;
        
        template<typename graph_t>
        value_type solve(
            graph_t& g,
            const node_pos_t Source, const node_pos_t Dest,
            const std::vector<value_type>& weight,
                  std::vector<value_type>& residual_cap)
        {
            value_type maxflow{0};
            
            // find the max-flow-anycost
            maxflow = maxflow_type::solve(
                g,Source,Dest,
                residual_cap,
                [](arc_pos_t)->bool{return true;});
            
            // return maxflow;
            
            std::vector<value_type> reduced_weight = weight;
            std::vector<value_type> potential(g.max_num_nodes(),0);
            std::vector<value_type> excess(g.max_num_nodes(),0);
            
            auto relabel = 
                [&](const node_pos_t x,value_type eps)
            {
                // std::cerr << " relabel " << x << " delta = " << eps << "\n";
            
                potential[x] -= eps;
                for(auto e : g.out_arcs(x))
                {
                    reduced_weight[e] -= eps;
                }
                for(auto e : g.in_arcs(x))
                {
                    reduced_weight[e] += eps;
                }
            };
            
            auto push_flow = 
                [&](arc_pos_t e,value_type delta)
            {
                    auto [src,dst] = g.arc_ends(e);
                    // std::cerr << " push flow at " << e 
                    //           << " (" << src << "," << dst << ")"
                    //           << " delta = " << delta << "\n";
                    
                    residual_cap[e]-=delta;
                    residual_cap[g.arc_dual(e)]+=delta;
                    
                    excess[src] -= delta;
                    excess[dst] += delta;
                    
                    // std::cerr << "push " << delta << " over " << e << '\n';
            };
            
            value_type maxC = 0;
            const int N = g.num_nodes();
            for(auto e : g.arcs())
            {
                reduced_weight[e] *= N;
                maxC = std::max(maxC,reduced_weight[e]);
            }
            maxC = lower_bound_power2(maxC);
            
            
            // int cycle=0;
            for(;maxC>0;maxC/=2){
                // cycle++;
                // std::cerr << "cycle " << cycle << " eps = " << maxC << '\n';
            
                // improve
                for(auto e : g.arcs())
                {
                    if(reduced_weight[e]<0 && residual_cap[e]>0)
                    {
                        push_flow(e,residual_cap[e]);
                    }
                    // this also does the trick of making the flow = 0 for arcs with
                    // reduced_weight>0, 
                }
                std::set<node_pos_t> active;
                for(auto n : g.nodes())
                if(excess[n]>0)
                {
                    active.insert(n);
                    // std::cerr << n << " is added to active\n";
                }
                // int ct=0;
                while(!active.empty())
                {
                    // ct++;
                    // if(ct>20)exit(1);
                
                    auto t = *active.begin();
                    
                    // std::cerr << t << " is active\n";
                    
                    bool pushed = false;
                    
                    for(auto e : g.out_arcs(t))
                    {
                        auto rw = reduced_weight[e];
                        auto rc = residual_cap[e];
                        if(rw<0 && rw>=-maxC && rc>0)
                        {
                            pushed = true;
                            auto [a,b] = g.arc_ends(e);
                            auto d = std::min(excess[a],rc);
                            
                            push_flow(e,d);
                            
                            if(excess[a]<=0)
                                active.erase(a);
                            if(excess[b]>0)
                                active.insert(b);
                            
                            break;
                        }
                    }
                    
                    if(!pushed)
                        relabel(t,maxC);
                }
            }
            // std::cerr << "done\n";
            return maxflow;
        }
        
        public:
        mincostflow_costScaling()
        {}
    };

}
