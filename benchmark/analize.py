import json
import matplotlib.pyplot as plt
import numpy

def open_json_data(filename):
    with open(filename,'r') as f:
        return json.load(f)

ortool_data = open_json_data('ortools.json')
apath_data = open_json_data('augmenting_path.json')
cscaling_data = open_json_data('cost_scaling.json')

def plot_success_rate(data):
    x = [ int(i) for i in data.keys() ]
    y = [ data[i]['nsuccess']/(data[i]['nsuccess']+data[i]['nfails']) for i in data.keys()  ]
    fig = plt.figure()
    ax = fig.subplots()
    ax.grid()
    ax.set_title('Success rate')
    ax.set_xlabel('amount (sats)')
    ax.set_ylabel('success rate')
    ax.loglog(x,y)
    fig.savefig('plot_success.png')
    plt.show()

def plot_time(data):
    fig=plt.figure()
    ax=fig.subplots()
    ax.grid()
    ax.set_title('MCF timing')
    ax.set_xlabel('amount (sats)')
    ax.set_ylabel('time (ms)')
    for k in data:
        D = data[k]
        xser = [ int(i) for i in D.keys() ]
        tser = [ numpy.mean(D[i]['time_mcf'])*1000 for i in D.keys() ]
        tmin = [ numpy.min(D[i]['time_mcf'])*1000 for i in D.keys() ]
        tmax = [ numpy.max(D[i]['time_mcf'])*1000 for i in D.keys() ]
        ax.fill_between(xser,tmin,tmax,alpha = 0.2)
        ax.loglog(xser,tser,label=k)
    ax.legend()
    fig.savefig('plot_time.png')
    plt.show()
    #x = [ int(i) for i in data['ortools'].keys() ]

def plot_totaltime(data):
    fig=plt.figure()
    ax=fig.subplots()
    ax.grid()
    ax.set_title('Total Payment Time')
    ax.set_xlabel('amount (sats)')
    ax.set_ylabel('time (ms)')
    for k in data:
        D = data[k]
        xser = [ int(i) for i in D.keys() ]
        tser = [ numpy.mean(D[i]['time_total'])*1000 for i in D.keys() ]
        tmin = [ numpy.min(D[i]['time_total'])*1000 for i in D.keys() ]
        tmax = [ numpy.max(D[i]['time_total'])*1000 for i in D.keys() ]
        ax.fill_between(xser,tmin,tmax,alpha = 0.2)
        ax.loglog(xser,tser,label=k)
    ax.legend()
    fig.savefig('plot_totaltime.png')
    plt.show()
    

#print(ortool_data)
#print(apath_data)
#print(cscaling_data)

plot_success_rate(ortool_data)
in_data =  {"ortools" : ortool_data, "cost_scaling" : cscaling_data, "augmenting_path" : apath_data} 
plot_time(in_data)
plot_totaltime(in_data)
