tmp=`mktemp`
exe=benchmark/benchmark-mcf
gen=../benchmark/gen.py

# lightning
N=2000
M=150000

N=800
M=6000

Mcap=200
Mcost=200

for i in `seq 10`; do
    echo ""
    python $gen $N $M $Mcap $Mcost > $tmp
    $exe < $tmp
    
done
