#!/bin/bash

#
# Compress netCDF files by converting them to netCDF-4 if needed
#
# (wrapper around ncks with netCDF-4 support)
#
# Urs Beyerle, Matthias Munnich, ETH
#

######### function definitions

# Function to display usage information
function usage() {
    sname=`basename $0`
    err=$1

    cat <<EOT

    $sname: Compression of netCDF files

        Usage: $sname [-19DdhMoOpqrsv] <netCDF file list>

        -1 (-2,...,-9)	Compression level (0-9) (default: 1).
        -d,-0,-D	Decompress. (-D decompress and convert to netCDF-3)
        -h		Print this help message.
        -k		Keep original. Output file: extension ".nc" is replaced by ".nz".
        -M <chunking> 	select NCO chunking policy (default rd1).
        -o <name> 	Output file name.
        -p		NetCDF pack and compress data (lossy compression, precission is reduced).
        -q		Quiet (do not inform about errors).
        -r		Recursively go down directory tree.
        -s		Report file size change.
        -v		Increase verbosity.

    Notes:
        - Compression levels higher than 1 usually don't lead to sufficient
        additional space savings to warrant the increased compression time.
        - Packed data are stored in 2-byte integers with an offset and a scale factor
        This is a lossy compression with often huge space saving (1 to 10% of original)
        If you don't need high precission, use this.

    Examples:
    1) Simple compression of netCDF file "somefile.nc":
        \$ $sname somefile.nc

    2) Decompression of a netCDF file "somefile.nc":
        \$ $sname -d somefile.nc

    3) Lossy compression of all netCDF files in the directory tree below "somedir":
        \$ $sname -rp somedir

EOT

    exit $err

}

### Function to display warnings
function warn (){
   # warn if we are not in quite mode
    if [[ $quite != "1" ]] ; then
        echo $*
    fi
}

# Function to display notifications
function notify (){
   # print notification if verbose >=1
    if (( $verbose >= "1" )) ; then
        echo $*
    fi
}

# Function to display informational messages
function info (){
   # print infos if verbose >=2
    if (( $verbose >= "2" )) ; then
        echo $*
    fi
}

# Function to check if NCO supports netCDF-4
function check_nco() {
ncks -r 2>&1 | grep -q netCDF4.*Yes
if [[ "$?" != "0" ]]; then
    echo
    echo "ERROR: Your ncks ($(which ncks)) does not support netCDF-4 !"
    echo
    exit 1
fi
}

# Function to check if ncdump supports netCDF-4
function check_ncdump() {
if [[ "$(nc-config --has-nc4)" != "yes" ]]; then
    echo
    echo "ERROR: Your netcdf library does not support netCDF-4 !"
    echo
    exit 1
fi
}

# Function to parse command-line options
function parse_options() {
    #default options
    level=1
    recursiv=0
    pack=0
    quite=0
    verbose=0
    keep=0
    ofile=''
    chunk='rd1'
    size=0
    format=4
    jobs=-1

    while getopts DdhM:ko:pqrsv0123456789  op ; do

        case $op in
            d)
                level=0;;
            D)
                format=3;
                level=0;;
            h)
                usage 0;;
            r)
                recursiv=1;;
            v)
                ((verbose++));;
            M)
                chunk=$OPTARG;;
            k)
                keep=1;;
            o)
                ofile=$OPTARG;;
            p)
                pack=1;;
            q)
                quite=1;;
            s)
                size=1;;
            [0-9] )
                level=$op;;
            *)
                echo Unknown option $op
                usage 1;;
        esac
    done

    shift $((OPTIND - 1))
    args=$*
    if  [[ "$ofile" != '' ]] ; then
      if [ "$#" != "1" ] ; then
        echo
        echo "  ERROR: only one input file allowed with option -o "
        echo "    (See $(basename $0) -h for usage)"
        echo
      fi
    fi

    info -e "Options: level = $level; recursiv = $recursiv; pack = $pack\n chunking= $chunk; file list: $*"
}

# Function to compress/pack & compress netCDF files
function compress () {
    local file=$1
    info  "Processing: $file ..."

    # Check if file exists
    if [[ ! -e $file ]]; then
	    info "INFO: $file not found - skipped!"
        continue
    fi

    # Check if file is writable
    if [[ ! -w $file  && $ofile == '' ]]; then
        info "INFO: $file not writable - skipped!"
        continue
    fi

    # Check if file is netCDF
    ncdump -k $file >/dev/null 2>&1
    if [[ "$?" != "0" ]]; then
        info "INFO: $file not a netCDF file - skipped!"
        continue
    fi


    # Get current deflation level
    inlevel=$(ncdump -hs $file | grep _DeflateLevel  | head -1 | awk '{print $3}')
    if [ "$inlevel" != "" ] ; then
        info INFO: Original _DeflationLevel = $inlevel
    fi
    if [ "$level" == "$inlevel" ] && [ "$pack" != "1" ]; then
        notify "First var has target compression - $file skipped."
        continue;
    fi

    if [[ $ofile == '' ]] ; then
        ftmp=$file.${ext}$$
    else
        ftmp=$ofile.${ext}$$
    fi

    if [ "$pack" != "1" ] ; then
        # lossless compress (i.e., no packing)
        notify Compressing $file ...
        ferr=/tmp/${sname}_error_$(basename $file .nc)$$.txt
        cmd="ncks -$format -L $level -a -O $file $ftmp"
        trap 'rm -f $ftmp*ncks.tmp' EXIT
        info $cmd 2>$ferr
        $cmd 2>$ferr
        err=$?
    else
        # Check if any variables contain a _FillValue attribute
        notify 'Packing (lossy)' $file ...
        ncdump -h $file | grep -q _FillValue
        if [ "$?" =  "0" ] ; then
            info INFO: converting to netCDF4 and removing _FillValue attribute
            # convert to netCDF4 to make _FillValue irrelevant
            ftmp0=${ftmp}.tmp
            # setup cleanup after interrupts
            trap 'rm -f $ftmp0*ncks.tmp' EXIT
            cmd="ncks -4 --cnk_map $chunk $file $ftmp0"
            info $cmd
            $cmd
            # change all _FillValue attributes
            cmd="ncatted -O -a _FillValue,,o,f,-32767 $ftmp0"
            info $cmd
            $cmd
            #ncatted -a _FillValue,,d,, $ftmp0 2> /dev/null
        else
            ftmp0=$file
        fi
        # Pack and compress/decompress
        trap 'rm -f $ftmp*ncpdq.tmp $ftmp' EXIT
        if [ "$level" = "0" ] ; then
           if [ "$format" = "3" ] ; then
	          cmd="ncpdq -P upk --64bit_data -O $ftmp0 $ftmp"
                  info $cmd
                  $cmd
           else
	          cmd="ncpdq -P upk -4 -L $level -O $ftmp0 $ftmp"
                  info $cmd
                  $cmd
           fi
        else
	       cmd="ncpdq -4 -L $level -O $ftmp0 $ftmp"
               info $cmd
               $cmd
        fi
        err=$?
        rm -f $ftmp0
    fi

    if [ "$err" = "0" ] ; then
       sorig=$(ls -s $file | awk '{print $1}')
       snew=$(ls -s $ftmp | awk '{print $1}')
      ((ratio=$snew*100/$sorig))
       if [ "$size" = "1" ] ; then
           echo New size: $(ls -sh $ftmp | awk '{print $1}') \($ratio%\)
       fi
	    # Reset timestamp, permissions, ownership
	touch -r $file $ftmp
        chmod --reference $file $ftmp
        if [ "$EUID" = "0" ] ; then
            # If we are root, change to owner of original file
            chown --reference $file $ftmp
        fi
	    # Replace orignal file
        if [[ "$ofile" != '' ]] ; then
            mv -f $ftmp $ofile
        elif [ "$keep" = "1" ] ; then
            mv -f $ftmp ${file%.nc}.nz
        else
	    mv -f $ftmp $file
        fi
        # Clean up
        if [ -f $ferr ] ; then
            rm -f $ferr
        fi
    else
	    warn "ERROR: $file compression failed - skipped!"
        warn Command: $cmd
        warn "More info: $ferr"
	    rm -f $ftmp
    fi
}


### Main script
[ $# -eq 0 ] && usage 1
check_nco
check_ncdump
parse_options $*
shift $((OPTIND - 1)) # Remove options form arg list

# Check if gnu_parallel can be found.
# Otherwise cancel parallel execution
# hash parallel >/dev/null 2>&1 || jobs=-1

for file in $args ; do
    if [[ -d $file ]] && [[ $recursiv == "1" ]]; then
        for f in $(find  $file  -type f ) ; do
           compress $f
        done
    else
        compress $file
    fi
done
