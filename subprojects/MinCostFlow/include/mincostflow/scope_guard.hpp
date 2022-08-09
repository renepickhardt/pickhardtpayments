#pragma once

/*
    credits to
    https://stackoverflow.com/questions/31365013/what-is-scopeguard-in-c
*/

#include <functional>       // std::function
#include <utility>          // std::move

namespace ln
{
    class Non_copyable
    {
    private:
        auto operator=( Non_copyable const& ) -> Non_copyable& = delete;
        Non_copyable( Non_copyable const& ) = delete;
    public:
        auto operator=( Non_copyable&& ) -> Non_copyable& = default;
        Non_copyable() = default;
        Non_copyable( Non_copyable&& ) = default;
    };

    class Scope_guard
        : public Non_copyable
    {
    private:
        std::function<void()>    cleanup_;

    public:
        friend
        void dismiss( Scope_guard& g ) { g.cleanup_ = []{}; }

        ~Scope_guard() { cleanup_(); }

        template< class Func >
        Scope_guard( Func const& cleanup )
            : cleanup_( cleanup )
        {}

        Scope_guard( Scope_guard&& other )
            : cleanup_( std::move( other.cleanup_ ) )
        { dismiss( other ); }
    };
}
