project('pickhardtpayments','cpp','c',
        default_options : ['cpp_std=c++17',
        'warning_level=3',
        'optimization=3'],
        version: '0.0.0')


libMCF_proj = subproject('MinCostFlow')
libMCF_dep  = libMCF_proj.get_variable('dep_mincostflow')
libMCF = libMCF_proj.get_variable('libmincostflow')

