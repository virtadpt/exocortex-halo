#!/usr/bin/env -S busybox sh

# system-script.sh - An experimental re-implementation of Systembot as a shell
#   script, suitable for deployment on embedded devices running OpenWRT,
#   and probably any Linux running ash or dash.  It outputs data to stdout
#   and errors to stderr.  You're on your own for getting the output someplace
#   to react to.
#
#   Accessory functions are as close to the functions that use them as
#   feasible.
#
#   This script requires the presence of the bc utility to do math.  If it's
#   not there it'll ABEND.

# by: The Doctor [412/724/301/703/415/510] <drwho at virtadpt dot net>
# License: GPLv3

# This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo).

# PLEASE READ THE README.MD FILE BEFORE ATTEMPTING TO USE THIS UTILITY.  THIS
# IS STILL A WORK IN PROGRESS.

# v0.3 - Added memory usage monitoring.
# v0.2 - Prototype release.

# TODO:
#   * Accept commands from outside.  Parse them and react.
#   * Online help (--help / -h)
#   * Debug mode (--debug / -d)
#   * Move the list length calculations into a separate function.
#   * Loadable (sourceable?) config file.
#   * System temperature (if detected?)
#   * Add a configurable cooldown period for each metric (i.e., only alert on
#     dangerous storage usage every n seconds/hours/whatever).  This might
#     take a little math.
#   * Network traffic stats?

# Debug mode?
DEBUG=0

# Maximum number of elements in each "array."
max_array_len=10

# Time in seconds to sleep in between loops.
cycle_time=10

# Number of standard deviations to worry about.
stddev=2

# Arrays for the statistical analysis of device metrics.
one_minute_load_history=""
five_minute_load_history=""
ten_minute_load_history=""

# Standard deviations.
one_minute_stddev=0
five_minute_stddev=0
ten_minute_stddev=0

# Percentage of disk space used which is considered too high.
disk_space_danger_zone=85

# Memory usage percentage which is considered too high.
memory_danger_zone=85

# Functions
# Library function which takes a list of numbers and calulates the average.
calculate_list_average () {
    # $1: Variable that holds the returned value.
    # $2: List of numbers to average.
    # $3: Length of the list of numbers.

    local result=$1
    local list_of_figures=$2
    local list_length=$3

    local average=0
    
    for i in $list_of_figures; do
        average=$( echo "$average + $i" | bc -l )
    done
    average=$( echo "scale=2; $average/$list_length" | bc -l )
    eval $result="'$average'"
}

# Library function which calculates the standard deviation
#   (https://en.wikipedia.org/wiki/Standard_deviation) of the numbers in a
#   list.
calculate_list_stddev () {
    # $1: Variable that holds the returned value.
    # $2: List of numbers to average.
    # $3: Length of the list of numbers.
    # $4: Average of the list of numbers.

    local result=$1
    local list_of_figures=$2
    local list_length=$3
    local average=$4

    # Local list which holds the deviations of the elements of the data set.
    local population=""

    # Length of the population list.
    local population_length=0

    # Variance of the population.
    local variance=0

    # Standard deviation of the population.
    local stddev=0

    # Calculate the deviation of each data point.
    for i in $list_of_figures; do
        deviation=$( echo "scale=2; ($i - $average) ^ 2" | bc -l )
        if [ $population_length -eq 0 ]; then
            population=$deviation
        else
            population="$population $deviation"
        fi
        population_length=$(( $population_length+1 ))
    done

    # Calculate the variance of the population.
    calculate_list_average variance "$population" $population_length

    # Calculate the standard deviation.
    stddev=$( echo "scale=2; sqrt($variance)" | bc -l )
    eval $result="'$stddev'"
}

# Primary function which gets and analyzes the system load on every loop.
analyze_system_load () {
    local one_minute_load_length=0
    local five_minute_load_length=0
    local ten_minute_load_length=0

    local one_minute_load_average=0
    local five_minute_load_average=0
    local ten_minute_load_average=0

    # Get system load.
    load=$(top -n 1 | grep '^Load average')
    one_minute_load=$(echo $load | awk '{print $3}')
    five_minute_load=$(echo $load | awk '{print $4}')
    ten_minute_load=$(echo $load | awk '{print $5}')

    # Calculate the lengths of the lists.
    for i in $one_minute_load_history; do
        one_minute_load_length=$(( $one_minute_load_length+1 ))
    done
    for i in $five_minute_load_history; do
        five_minute_load_length=$(( $five_minute_load_length+1 ))
    done
    for i in $ten_minute_load_history; do
        ten_minute_load_length=$(( $ten_minute_load_length+1 ))
    done

    # Append the new readings to the lists.
    if [ $one_minute_load_length -eq 0 ]; then
        one_minute_load_history=$one_minute_load
    else
        one_minute_load_history="$one_minute_load_history $one_minute_load"
    fi
    one_minute_load_length=$(( $one_minute_load_length+1 ))

    if [ $five_minute_load_length -eq 0 ]; then
        five_minute_load_history=$five_minute_load
    else
        five_minute_load_history="$five_minute_load_history $five_minute_load"
    fi
    five_minute_load_length=$(( $five_minute_load_length+1 ))

    if [ $ten_minute_load_length -eq 0 ]; then
        ten_minute_load_history=$ten_minute_load
    else
        ten_minute_load_history="$ten_minute_load_history $ten_minute_load"
    fi
    ten_minute_load_length=$(( $ten_minute_load_length+1 ))

    # Measure the length of each list and drop the oldest value if it's longer
    # than the configured maximum.
    if [ $one_minute_load_length -gt $max_array_len ]; then
        one_minute_load_history=$(echo $one_minute_load_history | \
            cut -d' ' -f2-)
    fi
    if [ $five_minute_load_length -gt $max_array_len ]; then
        five_minute_load_history=$(echo $five_minute_load_history | \
            cut -d' ' -f2-)
    fi
    if [ $ten_minute_load_length -gt $max_array_len ]; then
        ten_minute_load_history=$(echo $ten_minute_load_history | \
            cut -d' ' -f2-)
    fi

    # Calculate the load averages.
    if [ $one_minute_load_length -gt 5 ]; then
        calculate_list_average \
            one_minute_load_average \
            "$one_minute_load_history" \
            $one_minute_load_length
    fi

    if [ $five_minute_load_length -gt 5 ]; then
        calculate_list_average \
            five_minute_load_average \
            "$five_minute_load_history" \
            $five_minute_load_length
    fi

    if [ $ten_minute_load_length -gt 5 ]; then
        calculate_list_average \
            ten_minute_load_average \
            "$ten_minute_load_history" \
            $ten_minute_load_length
    fi

    # Calculate the standard deviation of each list of values.
    if [ $one_minute_load_length -gt 5 ]; then
        calculate_list_stddev \
            one_minute_stddev \
            "$one_minute_load_history" \
            $one_minute_load_length \
            $one_minute_load_average

        # Once again, shells not doing floating point math bites us in the
        # ass.  Thankfully `bc` can help here, too.
        if [ $( echo "$one_minute_stddev >= $stddev" | bc -l ) -ne 0 ]; then
            echo "The system load has spiked to $one_minute_load on the one minute average."
            echo "This is $one_minute_stddev standard deviations beyond what is safe."
        fi
    fi

    if [ $five_minute_load_length -gt 5 ]; then
        calculate_list_stddev \
            five_minute_stddev \
            "$five_minute_load_history" \
            $five_minute_load_length \
            $five_minute_load_average

        if [ $( echo "$five_minute_stddev >= $stddev" | bc -l ) -ne 0 ]; then
            echo "The system load has spiked to $five_minute_load on the five minute average."
            echo "This is $five_minute_stddev standard deviations beyond what is safe."
        fi
    fi

    if [ $ten_minute_load_length -gt 5 ]; then
        calculate_list_stddev \
            ten_minute_stddev \
            "$ten_minute_load_history" \
            $ten_minute_load_length \
            $ten_minute_load_average

        if [ $( echo "$ten_minute_stddev >= $stddev" | bc -l ) -ne 0 ]; then
            echo "The system load has spiked to $ten_minute_load on the ten minute average."
            echo "This is $ten_minute_stddev standard deviations beyond what is safe."
        fi
    fi
}

# Primary function which gets and analyzes storage space usage for non-in
#   memory and non-read only file systems on each loop.
analyze_storage_space () {

    local filesystems=""

    # Isolate the filesystems we care about.
    filesystems=$( mount | egrep -v '(ro|sysfs|tmp|devpts|debugfs)' )
    filesystems=$( echo $filesystems | awk '{print $3}' )

    # Having /overlay around confuses things.  We can't actually get its disk
    # space reading.  However, it's the same filesystem as /, so we're not
    # actually losing anything.
    filesystems=$( echo $filesystems | grep -v 'overlay' )

    # Fuzz out the disk space used for every remaining filesystem.
    for i in $filesystems; do
        local fs=""
        local usage=0

        fs=$(df -h $i | tail -n1 | awk '{ print $6 }')
        usage=$(df -h $i | tail -n1 | awk '{ print $5 }' | sed 's/%//')

        # Is the filesystem in the danger zone?
        if [ $( echo "$usage >= $disk_space_danger_zone" | bc -l ) -ne 0 ]; then
            echo "Warning: Filesystem $fs is at $usage% of capacity."
            echo "This is too close to the configured danger zone."
            echo "Please investigate this system at your earliest convenience."
        fi
    done
}

# Primary function which monitors memory utilization on the device.
analyze_memory_usage () {

    local memory=""
    local memory_total=""
    local memory_used=""
    local memory_free=""

    # Get the current memory usage situation.
    memory=$( free -m | grep '^Mem' )
    memory_total=$( echo $memory | awk '{ print $2 }' )
    memory_used=$( echo $memory | awk '{ print $3 }' )
    memory_free=$( echo $memory | awk '{ print $4 }' )

    # Compute memory usage as a percentage.  This is the cleanest way I know
    # of to get an integer result.
    memory=$( echo "scale=2; ( $memory_used / $memory_total ) * 100" | bc -l )
    memory=$( echo "$memory / 1" | bc )

    # Test the memory stats.
    if [ $memory -ge $memory_danger_zone ]; then
        echo "WARNING: Memory utilization is at $memory% of maximum."
        echo "Please investigate before system stability is impacted."
    fi
}

# check_system_temperature () {
# }

# Setup the script environment.
# See if bc is present.  If it's not, ABEND.
which bc > /dev/null
if [ $? -gt 0 ]; then
    echo "ERROR: bc is not installed.  This utility won't work without it."
    echo "       Install that package and try again."
    exit 1
fi

# Main loop.
while true; do
    analyze_system_load
    analyze_storage_space
    analyze_memory_usage

    echo "Sleeping..."
    sleep $cycle_time
    echo
done

# Fin.
exit 0

