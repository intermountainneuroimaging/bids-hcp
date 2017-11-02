#needed to clean up some of the numerical config options (if empty or non-numerical, output empty)
print_decimal_number () { echo $1 | awk '{if($1*1 == $1) printf "%.15f\n", $1; else print ""}'; };

timestamp () { date +"%Y-%m-%d %H:%M:%S %Z"; }
