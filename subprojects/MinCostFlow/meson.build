project('MinCostFlow','cpp',
    default_options: [
        'warning_level=3',
        'debug=true',
        'optimization=3',
        'cpp_std=c++17'])

subdir('include')

libmincostflow = library('mincostflow',
    my_headers,
    include_directories: my_includedir,
    install: true)

dep_mincostflow = declare_dependency(link_with: libmincostflow,include_directories: my_includedir)

install_headers(my_headers,subdir: 'mincostflow')

subdir('test')
subdir('examples')
subdir('benchmark')
