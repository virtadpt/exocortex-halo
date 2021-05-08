#!/bin/busybox sh

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
#
#   Temperature monitoring will only work if you have the lm-sensors package
#   installed.

# by: The Doctor [412/724/301/703/415/510] <drwho at virtadpt dot net>
# License: GPLv3

# This is part of the Exocortex Halo project
#   (https://github.com/virtadpt/exocortex-halo).

# PLEASE READ THE README.MD FILE BEFORE ATTEMPTING TO USE THIS UTILITY.  THIS
# IS STILL A WORK IN PROGRESS.

# v0.4 - Added temperature monitoring.
# v0.3 - Added memory usage monitoring.
# v0.2 - Prototype release.

# TODO:
#   * Accept commands from outside.  Parse them and react.
#   * Online help (--help / -h)
#   * Debug mode (--debug / -d)
#   * Move the list length calculations into a separate function.
#   * Loadable (sourceable?) config file.
#   * Add a configurable cooldown period for each metric (i.e., only alert on
#     dangerous storage usage every n seconds/hours/whatever).  This might
#     take a little math.
#   * Network traffic stats?
#   * Add a config feature which sets Celsius, Fahrenheit, or Kelvin for the
#     temperature outputs.

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

# Flag that determines whether or not device sensors can be accessed.
sensors_available=1

# Directory that holds text files that contain device sensor readings.  We do
# this because ash doesn't support associative arrays/hash tables.  There are
# undoubtedly worse ways of doing it but there's no reason to make it suck any
# more than it already does.
sensor_readings_dir="/tmp/sensors"

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

# This helper function populates a list with the names of the lm sensors
#   chips on the device.  This is to make parsing their data significantly
#   easier later.
find_temperature_sensors () {
    if [ -d $sensor_readings_dir ]; then
        echo "Regenerating device's temperature sensor records."
        rm -rf $sensor_readings_dir
    fi
    mkdir $sensor_readings_dir

    # Each sensor gets its own tempfile.  File paths will look like this:
    #   /tmp/sensors/tmp421-i2c-0-4c.temp1
    for i in $( sensors -A | grep -v '^temp' | grep -v '^$' ); do
        for j in $( sensors -f $i | grep '^temp' | awk '{print $1}' | sed 's/:$//' ); do
            touch $sensor_readings_dir/$i.$j
        done
    done
}

# Primary function which interrogates the temperature sensors and determines
#   whether or not one of them has spiked to dangerous levels.
check_system_temperature () {

    # The output for a sensor will look something like this:
    #   Adapter: mv64xxx_i2c adapter
    #   temp1:       +121.5°F  
    #   temp2:       +124.4°F  
    for i in $sensor_readings_dir/*; do

        # Skip backup files.  Source:
        #   https://github.com/dylanaraps/pure-sh-bible
        case $i in
            *.bak)
                continue
        esac

        # We need a list of values for the heavy math later.
        local temperature_list=""

        # We also need variables to hold diced-up filenames.
        local chip=""
        local sensor=""
        local temp=""

        # Variables for the temperature readings.
        local temperature=""
        local sum_of_temperatures=0
        local temperature_list=""
        local number_of_samples=0
        local temperature_average=0

        # Calculated standard deviation of the sensor's temperature history.
        local sensor_stddev=0

        # Suss out the temperatures for each sensor.  There can be (and usually
        # is) more than one per sensor, and is stored as the file extension.
        chip=$( basename $i )
        sensor=$( echo $chip | awk -F. '{print $1}' )
        temp=$( echo $chip | awk -F. '{print $2}' )

        # It would be really nice if the sensors utility would just print
        # the temperature reading for a particular chip and a particular
        # sensor, but whatever.
        temperature=$( sensors -f -A $sensor | grep $temp | awk '{print $2}' | sed 's/+//' | sed 's/°//' | sed 's/F$//i' | sed 's/C$//i' )

        # Calculate the sum of the temperatures from that file.
        for j in $( cat $i ); do
            sum_of_temperatures=$( echo "$sum_of_temperatures + $j" | bc -l )

            # We also need to build a list of temperature samples.
            temperature_list="$temperature_list $temperature"
        done
        sum_of_temperatures=$( echo "$sum_of_temperatures + $temperature" | bc -l )

        # Calculate length of tempfile.
        number_of_samples=$( wc -l $i | awk '{print $1}' )

        # Save the new sample to the tempfile.
        if [ -f $i.bak ]; then
            rm -f $i.bak
        fi
        mv -f $i $i.bak
        tail -$(( $max_array_len-1 )) $i.bak > $i
        echo $temperature >> $i

        # Catch the "just started up" condition, where we don't have enough
        # samples to do the math right.  Or at all. #divbyzero
        if [ $( echo "$number_of_samples < $max_array_len" | bc -l ) -ne 0 ]; then
            continue
        fi

        # Calculate the average of the temperatures.
        calculate_list_average temperature_average "$temperature_list" \
            $number_of_samples

        # Calculate the standard deviation.
        calculate_list_stddev sensor_stddev "$temperature_list" \
            $number_of_samples $temperature_average

        # If the temperature has jumped x standard deviations, complain.
        if [ $( echo "$sensor_stddev > $stddev" | bc -l ) -ne 0 ]; then
            echo "WARNING: Temperature sensor $chip has climbed to $temperature degrees Fahrenheit."
            echo "This is $sensor_stddev over the recorded history.  Investigate immediately."
        fi
    done
}

# Core code.
# See if bc is present.  If it's not, ABEND.
which bc > /dev/null
if [ $? -gt 0 ]; then
    echo "ERROR: bc is not installed.  This utility won't work without it."
    echo "       Install that package and try again."
    exit 1
fi

# See if the lm-sensors package is installed.  If it's not disable temperature
# monitoring.
pkg_installed=$(opkg list-installed | grep lm-sensors | wc -l)
if [ $pkg_installed -ne 1 ]; then
    echo "Package lm-sensors not installed.  Disabling temperature monitoring."
    sensors_available=0
fi

# See if the sensors are accessible.  If not, disable temperature monitoring.
sensors 1>/dev/null 2>/dev/null
if [ $? -gt 0 ]; then
    echo "Unable to probe sensors.  Disabling temperature monitoring."
    sensors_available=0
fi

# Set up the list of temperature sensors.
if [ $sensors_available -eq 1 ]; then
    find_temperature_sensors
fi

# Main loop.
while true; do
    analyze_system_load
    analyze_storage_space
    analyze_memory_usage

    if [ $sensors_available -gt 0 ]; then
        check_system_temperature
    fi

    echo "Sleeping..."
    sleep $cycle_time
    echo
done

# Fin.
exit 0

