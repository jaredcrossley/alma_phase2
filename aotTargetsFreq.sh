#!/bin/bash
# aotTargetsFreq.sh
# Richard Simon 2013Oct31
#
# Extracts summary parameters from .aot files
# Extracts a list of targets from a .aot file into a formatted table
# Usage: ./aotTargets.sh <aot file name> <HR>
#     aot file name is required
#     specifying the HR parameter will provide a friendlier output format


# Step 1:  Use the name of the .aot file to name the output file.  Delete it if it already exists
targetsFile=`echo $1 | sed s/.aot//`_Targets.txt
touch $targetsFile
rm $targetsFile


# Step 2:  Unzip the .aot file to a temporary directory after deleting any existing version
exp=expanded_aot_file
if [ -d $exp ]; then rm -r $exp; fi
unzip -d $exp $1 > /dev/null

# Step 3:  Extract summary parameters from the ObsProject.xml file

# Project Code, version and save time
projCode=`cat ./$exp/ObsProject* | grep "<prj:code>" | sed -n 's/<\/.*//; s/.*>//p'`
projVersion=`cat ./$exp/ObsProject* | grep "<prj:version>" | sed -n 's/<\/.*//; s/.*>//p'`
projTime=`cat ./$exp/ObsProject* | grep -m 1 "timestamp=" | sed -n 's/.*mp=.//; s/\..*//; s/T/ /p'`
projPI=`cat ./$exp/ObsProposal.xml | sed '/<prp:PrincipalIn/,/<\/prp:PrincipalIn/!d; /fullName/!d' |sed 's/<\/.*//; s/.*>//'`

# Step 4:  Check that SchedBlock.xml files exist; if not it means that this project hasn't been generated / isn't phase 2
if [ -f ./$exp/SchedBlock0.xml ]; then
    # echo the SB file exists
    isPhase2="true"
else
    echo "   Project     "
    echo $projCode PH1
    exit
fi


# Step 5: Loop through the Schedule blocks

# Get the list of SchedBlock files for the loop and start the loop. i will be the file number
iSB=0
ls -1 ./$exp/SchedBlock* |\
while read SBfile; do

    # Load the SB into a single LARGE 1 line variable(!):
    SB=`cat $SBfile`

    # SB file name without path
    SBfileShort=`echo $SBfile | sed -e 's/^.*\///'`

    # Schedule block name from the prj:name parameter
    SBname=`echo $SB | sed 's/.*<prj:name>//;s/<\/prj:name.*//'`

    # Skip over schedule blocks with status="NewPhase1" - they haven't been generated yet
    if [ $(echo $SB | sed -n 's/.*status="//p' |sed 's/".*//') = "NewPhase1" ]; then
        continue
    fi
    # Will use this file, so increment counter
    (( iSB++ ))

    # Get the SchedBlockEntity entityId for this ScheduleBlock (applies to all targets in the SB)
    SBEId=`cat $SBfile | sed -n '/SchedBlockEntity entityId=/s/\(.*="\)\(.*[A-z,0-9]\).$/\2/p' |sed 's/\//\\\\\//g'` # Note escape character "\" is added into $SBEId as needed
    # echo "SB Entity Id: "$SBEId

    # Get the largest angular scale from the ObsProject.xml
    # First find the entityPartID associated with the Science Goal for this SB
    #    Reverse the line order of the file
    #    In the reversed lines, select all of the ObsUnitSet by finding the end of the previous OUS or the beginning of the SG
    #    Set the line order back to normal
    #    Find the entityPartId's associated with an OUS
    #    Select the first such entityPartId 

    scienceGoalId=`cat ./$exp/ObsProject.xml |\
        sed '/<sbl:sourceEphemeris>/,/<\/sbl:sourceEphemeris>/d' |\
        sed '1,/'$SBEId'/ !d' |\
        sed '1!G;h;$!d'  |\
        sed '1,/<prj:ObsPlan status=\"/!d' |\
        sed '1!G;h;$!d'  |\
        sed '/<prj:ObsUnitSet status/,$ !d' |\
        sed '1,3!d' |\
        sed -n '/ entityPartId/ s/.* entityPartId=\"//p' |\
        sed 's/\".*//'`
    # echo "SG partID:"$scienceGoalId

    largestAngScale=`cat ./$exp/ObsProject.xml |\
        sed -n '/'$scienceGoalId'/,/desiredLargestScale/p' |\
        sed -n '/desiredLargestScale/s/<\/.*//p' |\
        sed -n '$s/.*="//;$s/">/ /p' |\
        sed 's/^/(/;s/arcsec/1.*/;s/arcmin/60.*/;s/deg/3600.*/;s/mas/0.001*/;s/$/)/'`
    # echo "Largest Ang Scale:"$largestAngScale
    largestAngScale=$(echo $largestAngScale | bc -l)
    # echo "Largest Ang Scale:"$largestAngScale  

    # Use the scienceGoalId to select the Science Goal section; save the rectangle definition for later
    # echo "start tempRectangle retrieval"
    cat ./$exp/ObsProject.xml |\
        sed '1,/'$scienceGoalId'/ d' |\
        sed '/<\/prj:ScienceGoal/,$ d' |\
        sed -n '/<prj:Rectangle>/,/<\/prj:Rectangle>/p' > tempRectangle.txt

    # Use the scienceGoalId to select the SpectralSetup section
    spectralParms=`cat ./$exp/ObsProject.xml |\
        sed '1,/'$scienceGoalId'/ d' |\
        sed '/<\/prj:SpectralSetup/,$ d' |\
        sed -n '/<prj:SpectralSetup/p'`

    pol=`echo $spectralParms | sed 's/.*polarisation="//;s/".*//'`
    if [[ "$pol" == "DOUBLE" ]]; then
        pol="Dual"
    else
        pol="XX"
    fi

    spType=`echo $spectralParms | sed 's/.*type="//;s/".*//'`
    if [[ "$spType" == "continuum" ]]; then
        spType="Cont"
    else
        spType="Line"
    fi
    # echo "Polarization:"$pol
    # echo "spType:"$spType
    
    # Use the scienceGoalId to get the requested angular resolution from the ObsProject.xml file for this SB
    angRes=`cat ./$exp/ObsProject.xml |\
        sed '1,/'$scienceGoalId'/ d' |\
        sed '/<\/prj:PerformanceParameters/,$ d' |\
        sed -n '/desiredAngularResolution/p' |\
        sed 's/ userUnit.*\">//; s/<\/.*//; s/.*="//; s/"/ /' |\
        sed 's/^/(/;s/arcsec/1.*/;s/arcmin/60.*/;s/deg/3600.*/;s/mas/0.001*/;s/$/)/'`
    angRes=$(echo $angRes | bc -l)
    # echo "angRes: "$angRes
    
    # Use the scienceGoalId to get the sensitivity goal from the ObsProject.xml file for this SB
    sensGoal=`cat ./$exp/ObsProject.xml |\
        sed '1,/'$scienceGoalId'/ d' |\
        sed '/<\/prj:PerformanceParameters/,$ d' |\
        sed -n '/<prj:desiredSensitivity unit="/p' |\
        sed 's/ userUnit.*\">//; s/<\/.*//; s/.*=\"//; s/\"/ /' |\
        sed 's/^/(/;s/Jy/10^3*/;s/mJy/1.*/;s/uJy/10^-3.*/;s/E/*10^/;s/$/)/'`
    # echo $sensGoal
    sensGoal=$(echo $sensGoal | bc -l)
    # echo "Sensitivity Goal: "$sensGoal

    # Step 5.1: For the current Schedule Block generate a file with a listing of the partIds for each target that is observed
    # This includes the partId parameters in the xml for
    #     Target (T);
    #     AbstractInstrumentSpecRef (AISR, the spectral setup used)
    #     FieldSourceRef (FSR, the field source); and 
    #     ObservingParametersRef (OPR, the observing parameters)
    # The file is in the form of bash variable assignments, one line per target
    cat $SBfile |\
        # Delete everything except Target blocks; concatenate lines that don't end in ">"
        sed -n '/<sbl:Target /,/<\/sbl:Target>/!d;/>$/!N;s/\n/ /;p' |\
        # 2nd round of concatenation
        sed '/>$/!N;s/\n/ /' |\
        # 3rd round of concatenation (usually not needed - do in case of future changes)
        sed '/>$/!N;s/\n/ /' |\
        # 4th round of concatenation (usually not needed - do in case of future changes)
        sed '/>$/!N;s/\n/ /' |\
        # delete ending line for target block; delete xml preambles
        sed '/<\/sbl:Targ/d;s/  *<sbl://' |\
        # Delete everything from " " to "artId" - will leave ="X..."
        sed 's/  *.*artId//' |\
        # Delete everything from " " to end of line
        sed 's/  *.*//' |\
        # Concatenate lines two by two (each target has 4 lines)
        sed 'N;s/\n/ /' |\
        # Concatenate lines again so each target is a single line; insert a ";" after each assignment; delete lower case letters
        sed 'N;s/\n/ /;s/" /"; /g;s/[a-z]*//g'  > setPartIds.tmp

    # Step 5.2: Find the partId for the representative target from the Schedule Constraints block
    Trep=`cat $SBfile |\
        sed '/<sbl:SchedulingConstraints/,/<\/sbl:SchedulingConstraints/!d' |\
        sed '/<sbl:representativeTargetRef/,/\/>/!d' |\
        tr -d '\n' |\
        sed 's/.* partId="//' |\
        sed 's/".*//'`
    # echo "partId for representative Target: "$Trep

    #   Step 5.3: Loop through the target list just created to find the representative target and calculate the dopplerFactor and bandwidths
    # echo "Start rep target"
    # cat setPartIds.tmp

    cat setPartIds.tmp |\
    while read targetCommand; do
        # echo $targetCommand
        # Step 5.3.1: Assign bash variables for the partId parameter for $T, $AISR, $FSR and $OPR for this target
        echo $targetCommand > temporaryCommand.sh
        chmod 755 ./temporaryCommand.sh
        source ./temporaryCommand.sh

        # Step 5.3.2: If this target is not the representative target then skip this target
        # echo "T, Trep: "$T $Trep
        if [ $T != $Trep ]; then
            continue
        fi

        # Step 5.3.3: Get the velocity for the representative target
        repVelocity=`cat $SBfile |\
            sed -n '/entityPartId=\"'"$FSR"'/,/<\/val:centerVelocity>/p'  |\
            sed -n '$s/<\/.*//p' |\
            sed 's/.*>//' `
        # echo "Representative Velocity: "$repVelocity

        # Step 5.3.3b: Get the Doppler Calculation Type for the representative target
        dopplerType=`cat $SBfile |\
            sed '1,/entityPartId=\"'"$FSR"'/d' |\
            sed '1,/ dopplerCalcType/!d'|\
            sed -n '/ dopplerCalcType="/s/^.*=\"//p'  |\
            sed 's/".*//'`
        # echo "Doppler Type: "$dopplerType

        # Step 5.3.4: Get the dopplerReference for the representative target from its spectral spec
        dopplerRef=`cat $SBfile |\
            sed -n '/entityPartId=\"'"$AISR"'/,/<\/sbl:SpectralSpec>/p'  |\
            sed -n '/dopplerReference/s/.*dopplerReference="//p' |\
            sed 's/".*//' `
        # echo "Doppler Reference: "$dopplerRef

        # Step 5.3.5: Calculate the dopplerFactor when the dopplerReference is "rest"
        if [[ "$dopplerRef" == "rest" ]]; then
            c=299792.458 # speed of light, km/s
            beta=$(echo '( '$repVelocity' / '$c' )' | bc -l)
            # echo "beta = v/c = "$beta
       
            if [[ "$dopplerType" == "RELATAVISTIC" ]]; then  # f(V) = f0 { (1-V/c)/(1+V/c) }^(1/2)
                # echo '( sqrt( (1.0-'$beta')*(1.0+'$beta')^-1 ) )' | sed 's/--/+/;s/+-/-/'
                dopplerFactor=$(echo '( sqrt( (1.0-'$beta')*(1.0+'$beta')^-1 ) )' | sed 's/--/+/;s/+-/-/' | bc -l)
            
            elif [[ "$dopplerType" == "OPTICAL" ]]; then # f(V) = f0 ( 1 + V/c )^(-1)
                # echo '( (1.0+'$beta')^-1 )' | sed 's/+-/-/'
                dopplerFactor=$(echo '( (1.0+'$beta')^-1 )' | sed 's/+-/-/' | bc -l)

            else # dopplerType is RADIO where f(V) = f0 ( 1 - V/c )
                # echo '( (1.0-'$beta') )' | sed 's/--/+/'
                dopplerFactor=$(echo '( (1.0-'$beta') )' | sed 's/--/+/' | bc -l)
            fi
        else
            dopplerFactor=1.0
        fi
        # echo "Doppler Factor: "$dopplerFactor

        # Step 5.3.6: Sky frequencies (spectral window centers) for representative target as a bash array
        echo 'k=0' > setSkyFreq.sh
        chmod 755 setSkyFreq.sh

            usingACA=`cat $SBfile | grep "arrayRequested=\"TWELVE-M"`
            if [[ "$usingACA" == "" ]]; then
                corr="ACA"
            else
                corr="BL"
            fi

	    cat $SBfile |\
            sed '/entityPartId=\"'"$AISR"'/,/<\/sbl:SpectralSpec>/!d'  |\
            sed -n '/<sbl:'$corr'SpectralWindow/,/<\/sbl:'$corr'SpectralWindow/p'   |\
            sed '/restFreq/!d' |\
            sed 's/.*="/spw[$k]=$(echo '\''(/;s/<.*/)'\'' | bc -l); (( k++ ))/;s/THz">/1000.*/;s/GHz">/1.*/;s/MHz">/.001*/' |\
            sed 's/\*/*'$dopplerFactor'*/' >> setSkyFreq.sh
        source ./setSkyFreq.sh
        # cat ./setSkyFreq.sh
        # echo "Representative Sky Frequencies: "${spw[@]}

        # Step 5.3.7: Spectral Window bandwidths for representative target as a bash array
        echo 'l=0' > setBandWidth.sh
        chmod 755 setBandWidth.sh
	    cat $SBfile |\
            sed '/entityPartId=\"'"$AISR"'/,/<\/sbl:SpectralSpec>/!d'  |\
            sed -n '/<sbl:effectiveBandwidth/p'   |\
            sed 's/.*="/bw[$l]=$(echo '\''(/;s/<.*/)'\'' | bc -l); (( l++ ))/;s/THz">/1000.*/;s/GHz">/1.*/;s/MHz">/.001*/' >> setBandWidth.sh
        source ./setBandWidth.sh
        # cat ./setBandWidth.sh
        # echo "Representative Band Widths: "${bw[@]}

    done

    #   Step 5.4: Loop through the target list for the selected Schedule Block
    mTarget=0
    cat ./setPartIds.tmp |\
    while read targetCommand; do

        # Step 5.4.1: Assign bash variables for the partId parameter for $T, $AISR, $RepSrc, $FSR and $OPR for this target
        echo $targetCommand > temporaryCommand.sh
        chmod 755 ./temporaryCommand.sh
        source ./temporaryCommand.sh

        # Step 5.4.2: Check the $FSR (Field Source block). If sourceName is "query" skip this target. Assumption is that sourceName block is on one line
        sourceName=`cat $SBfile |\
            sed -n '/entityPartId=\"'"$FSR"'/,/<\/sbl:sourceName>/p' |\
            sed '/<sbl:sourceName>/!d;s/<\/.*//' |\
            sed 's/.*>//'`
        if [ $sourceName == "query" ]; then
            continue
        fi
        (( mTarget++ ))
        # echo "Source name: "$sourceName

        # Step 5.4.3: Get the RA and Dec (Source coordinates) for the selected target in degrees
        sourceLongLat=`cat $SBfile |\
            sed '1,/entityPartId=\"'"$FSR"'/ d' |\
            sed '/<\/sbl:sourceCoordinates/,$ d ' |\
            sed -n '/val:l.*itude/s/<\/.*/))/p' |\
            sed 's/^.*=\"//;s/mas/(3600000.0^-1*(/g;s/arcsec/(3600.0^-1*(/g;s/arcmin/(60.0^-1*(/g;s/deg/(1.0*(/g' |\
            sed 's/">//' | bc -l |\
            sed 'N;s/\n/,/'`
        # echo "Source Long Lat: "$sourceLongLat

        # Get the array type and set use7m and useTP
         arrayType=`cat $SBfile |\
            sed -n '/arrayRequested/s/.*arrayRequested="//p' |\
            sed 's/".*//'`
         if [[ "$arrayType" == "TP-Array" ]]; then
             useTP="Y"
             use7m="N"
         elif [[ "$arrayType" == "SEVEN-M" ]]; then
             use7m="Y"
             useTP="N"
         else
             useTP="N"
             use7m="N"
         fi
         # echo "Use 7m:"$use7m
         # echo "Use TP:"$useTP
 

        # Step 5.4.4: Get number of pointings for the selected target
        cat $SBfile |\
            sed -n '/entityPartId=\"'"$FSR"'/,/<\/sbl:PointingPattern>/p'  |\
            sed -n '/<sbl:PointingPattern/,$s/<\/.*/))+/p' |\
            sed '/longitude /!d;s/^.*=\"//;s/mas/(3600000.0^-1*(/g;s/arcsec/(3600.0^-1*(/g;s/arcmin/(60.0^-1*(/g;s/deg/(1.0*(/g' |\
            sed 's/">//'  > tempLongitudes.txt
        numPointings=`cat tempLongitudes.txt | wc -l | sed 's/ //g'`
	
        isMosaic=`cat $SBfile |\
            sed -n '/entityPartId=\"'"$FSR"'/,/<\/sbl:PointingPattern>/p'  |\
            sed -n '/.*<sbl:isMosaic>/s///p' |\
            sed 's/<.*//'`
        # echo "isMosaic: "$isMosaic
        # echo "Number of pointings: "$numPointings

	# Set values for Mosaic parameters
        if [[ "$isMosaic" == "true" ]]; then
            paDeg=`cat tempRectangle.txt |\
                sed -n '/:pALong/s/.*="//p' |\
                sed 's/">/ /;s/<\/.*/))/' |\
                sed 's/mas/(3600000.0^-1*(/g;s/arcsec/(3600.0^-1*(/g;s/arcmin/(60.0^-1*(/g;s/deg/(1.0*(/g' | bc -l`
            longR=`cat tempRectangle.txt |\
                sed -n '/:long /s/.*="/(/p' |\
                sed 's/">/ /;s/<\/.*/)/' |\
                sed 's/arcsec/1.*/;s/arcmin/60.*/;s/deg/3600.*/;s/mas/0.001*/' | bc -l`
            shortR=`cat tempRectangle.txt |\
                sed -n '/:short/s/.*="/(/p' |\
                sed 's/">/ /;s/<\/.*/)/' |\
                sed 's/arcsec/1.*/;s/arcmin/60.*/;s/deg/3600.*/;s/mas/0.001*/' | bc -l`
            # echo $paDeg,$longR,$shortR
        else
            paDeg=0.
            longR=0.
            shortR=0.
        fi        
        # Step 5.4.4: Get the average Latitude offset in degrees for the selected target in case an offset or mosaic was used
        cat $SBfile |\
            sed -n '/entityPartId=\"'"$FSR"'/,/<\/sbl:PointingPattern>/p'  |\
            sed -n '/<sbl:PointingPattern/,$s/<\/.*/))+/p' |\
            sed '/latitude /!d;s/^.*=\"//;s/mas/(3600000.0^-1*(/g;s/arcsec/(3600.0^-1*(/g;s/arcmin/(60.0^-1*(/g;s/deg/(1.0*(/g' |\
            sed 's/">//'  > tempLatitudes.txt

        # Step 5.4.5: Get the velocity the selected target
        # sourceVelocity=`cat $SBfile |\
        #     sed -n '/entityPartId=\"'"$FSR"'/,/<\/val:centerVelocity>/p'  |\
        #     sed -n '$s/<\/.*//p' |\
        #     sed 's/.*>//' `
        # echo "Source Velocity: "$sourceVelocity

        # Step 5.4.5b: Get the receiver band for the representative target from its spectral spec
        rxBand=`cat $SBfile |\
            sed -n '/entityPartId=\"'"$AISR"'/,/<\/sbl:SpectralSpec>/p'  |\
            sed -n '/receiverBand/s/.*receiverBand="//p' |\
            sed 's/".*//' `
        # echo "Receiver Band: "$rxBand

        # Step 5.4.6: Number of spectral channels for each spw
        echo 'n=0' > setSpecChan.sh
        chmod 755 setSpecChan.sh

	cat $SBfile |\
            cat $SBfile |\
            sed '/entityPartId=\"'"$AISR"'/,/<\/sbl:SpectralSpec>/!d'  |\
            sed -n '/<sbl:spectralAveragingFac/p;/<sbl:effectiveNumberOfChan/p' |\
            sed 's/<\/.*Ch.*//;s/<\/.*/.^-1 * /;s/.*r>/nChan[$n]=\$(echo '\''(/;N;s/\n/ /' |\
            sed 's/<\/.*/)'\'' | bc -l); (( n++ ))/;s/  *<.*>/ /' >> setSpecChan.sh
        source ./setSpecChan.sh
        # cat ./setSpecChan.sh
        # echo "Spectral Channels: "${nChan[@]}

        # Step 5.4.7: rmsBW in GHz
 	    rmsBW=$(cat $SBfile |\
            sed -n '/<sbl:representativeBand/s/<\/.*/)/p' |\
            sed 's/.*=\"/(10^ /;s/\">/  /;s/ GHz/0*/;s/ MHz/-3*/;s/ kHz/-6*/;s/ Hz/-9*/' | bc -l)
        # echo "rmsBW: "$rmsBW

        # Step 5.4.9: Print the target information to standard out for debugging and test
        # echo ""
        # echo "Project Code:    "$projCode
        # echo "Project Version: "$projVersion
        # echo "Project Saved:   "$projTime
        # echo "Project PI:      "$projPI
        # echo "SchedBlock name: "$SBname
        # echo "SchedBlock file: "$SBfileShort
        # echo "Target name:     "$sourceName
        # echo "Long, Lat (deg): "$sourceLongLat
        # echo "Receiver Band:   "$rxBand
        # echo "Num of pointings:"$numPointings
        # echo "Mosaic:"         "$isMosaic
        # echo "Ang. Res. arcsec:"$angRes
        # echo "LargestAngScale: "$largestAngScale
        # echo "rmsBW (GHz):     "$rmsBW
        # echo "rmsGoal (mJy):   "$sensGoal
        source ./setSkyFreq.sh
        source ./setBandWidth.sh
        source ./setSpecChan.sh
        # echo "SPWs (GHz, Sky): "${spw[@]}
        # echo "SPW BWs (GHz):   "${bw[@]}
        # echo "SPW Chans (#):   "${nChan[@]}
        
        # Step 5.4.8: Formatted output - default is full table with 1 header line; command line option HR for human readable
        HR=0
        if [[ -n "$2" ]]; then
            if [ $2 = "HR" ]; then
                HR=1
            fi
        fi

        if [ $HR -eq 0 ]; then
            # Standard format with every field on every line
            if [ $iSB -eq 1 ]; then
                if [ $mTarget -eq 1 ];then
                    # Header line at start of targets table and a complete 1st line with project, SB, and target info
                    printf "%10s %7s %11s %8s %17s %40s %30s %11s %4s %7s %8s %22s %11s %11s %5s %6s %6s %6s %10s %2s %2s %4s %4s" \
                           "Project" "Vsn" "Saved Date" "Time" "PI" "SB Name" "SB file" "AngRes" "LAS" "rmsGoal" "rmsBW" "Source Name" "RA" "Dec" "Pnts" "PA_deg" "long" "short" "Band" "7m" "TP" "Type" "Pol."
                    i=0
                    while [ $i -lt $k ]; do
                        printf "    SPW   BW  nChan"
                        (( i++ ))
                    done
                    printf "\n"
                fi
            fi
            # Complete 1 line summary in table form
            # we need 1 line per mosaic, 1 line per pointing for non-mosaics
            if [[ "$isMosaic" == "true" ]]; then
                noff=$numPointings
                nn=$numPointings
            else
                noff=1
                nn=1
            fi
            while [ $noff -le $numPointings ]; do
                if [[ "$isMosaic" == "true" ]]; then
                    offsetLat=0.
                    offsetLong=0.
                else
                  offsetLat=`cat tempLatitudes.txt | sed -n ''$noff's/+//p' | bc -l`
                  offsetLong=`cat tempLongitudes.txt | sed -n ''$noff's/+//p' | bc -l`
                fi
                echo $projCode,$projVersion,$projTime,$projPI,$SBname,$SBfileShort,$angRes,$largestAngScale,$sensGoal,$rmsBW,$sourceName,$sourceLongLat,$offsetLong,$offsetLat,$nn,$paDeg,$longR,$shortR,$rxBand,$use7m,$useTP,$spType,$pol |\
                awk -F "," '{printf "%14s  %02d  %19s %20s %40s %30s %7.3f %5.2f %7.3f %8.6f %24s %11.7f %11.7f %3d %6.2f %6.2f %6.2f %10s %2s %2s %4s %4s", \
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,($12+$14),($13+$15),$16,$17,$18,$19,$20,$21,$22,$23,$24}'
                i=0
                while [ $i -lt $k ]; do
                    echo ${spw[$i]},${bw[$i]},${nChan[i]} |awk -F "," '{printf " %7.2f %5.3f %4.0f", $1,$2,$3}'
                    (( i++ ))
                done
                echo"" |awk '{printf "\n"}'
	        # echo $sourceLongLat,$offsetLong,$offsetLat,"1"
                (( noff++ ))
            done
        else
            # Selected HR option for more human readable format, project info not in individual lines
            # Project information:
            
            if [ $iSB -eq 1 ]; then
                # Project information:
                if [ $mTarget -eq 1 ];then
                    # Project information:
                    printf "(%s  PI:%s %s; Version:%d; Saved:%s %s)\n" $projCode $projPI $projVersion $projTime

                    # Header line at start of targets table and a complete 1st line with project, SB, and target info
                    printf "%22s %16s %11s %7s %8s %22s %11s %12s    %4s" \
                        "SB Name" "SB file" "AngRes" "rmsSens" "rmsBW" "Source Name" "RA" "Dec" "Pnts"
                    i=0
                    while [ $i -lt $k ]; do
                        printf "  [SPW   BW  nChan]"
                        (( i++ ))
                    done
                    printf "\n"

                    # SB + target 1 line summary
                    echo $SBname,$SBfileShort,$angRes,$sensGoal,$rmsBW,$sourceName,$sourceLongLat,0,0,$numPointings |\
	                awk -F "," '{printf "%26s %16s %7.3f %7.3f %8.6f %24s  %02d:%02d:%06.3f %3.0f:%02d:%05.2f %3d", \
                        $1,$2,$3,$4,$5,$6,($7+$9)/15, (($7+$9)/15)%1*60, (($7+$9)*4)%1*60, int(($8+$10))+($8+$10)/1000000, \
                        (($8+$10)<0?-($8+$10):($8+$10))*60%60, (($8+$10)<0?-($8+$10):($8+$10))*3600%60,$11}'
                    i=0
                    while [ $i -lt $k ]; do
                        echo ${spw[$i]},${bw[$i]},${nChan[i]} |awk -F "," '{printf " %7.2f %5.3f %4.0f", $1,$2,$3}'
                        (( i++ ))
                    done
                    echo"" |awk '{printf "\n"}'
                else
                    # Target information only for remaining targets in 1st SB
                    echo "","","","","",$sourceName,$sourceLongLat,0,0,$numPointings |\
	                awk -F "," '{printf "%26s %16s %7s %7s %8s %24s  %02d:%02d:%06.3f %3.0f:%02d:%05.2f %3d", \
                        $1,$2,$3,$4,$5,$6,($7+$9)/15, (($7+$9)/15)%1*60, (($7+$9)*4)%1*60, int(($8+$10))+($8+$10)/1000000, \
                        (($8+$10)<0?-($8+$10):($8+$10))*60%60, (($8+$10)<0?-($8+$10):($8+$10))*3600%60, $11}'
                    i=0
                    while [ $i -lt $k ]; do
                        echo ${spw[$i]},${bw[$i]},${nChan[i]} |awk -F "," '{printf " %7.2f %5.3f %4.0f", $1,$2,$3}'
                        (( i++ ))
                    done
                    echo"" |awk '{printf "\n"}'
                fi
            elif [ $mTarget -eq 1 ];then
                # First line for a target includes SB specific information
                    echo $SBname,$SBfileShort,$angRes,$sensGoal,$rmsBW,$sourceName,$sourceLongLat,0,0,$numPointings |\
	                awk -F "," '{printf "%26s %16s %7.3f %7.3f %8.6f %24s  %02d:%02d:%06.3f %3.0f:%02d:%05.2f %3d", \
                        $1,$2,$3,$4,$5,$6,($7+$9)/15, (($7+$9)/15)%1*60, (($7+$9)*4)%1*60, int(($8+$10))+($8+$10)/1000000, \
                        (($8+$10)<0?-($8+$10):($8+$10))*60%60, (($8+$10)<0?-($8+$10):($8+$10))*3600%60, $11}'
                i=0
                while [ $i -lt $k ]; do
                    echo ${spw[$i]},${bw[$i]},${nChan[i]} |awk -F "," '{printf " %7.2f %5.3f %4.0f", $1,$2,$3}'
                    (( i++ ))
                done
                echo"" |awk '{printf "\n"}'
            else
                # Target information only for remaining targets in an SB
                    echo "","","","","",$sourceName,$sourceLongLat,0,0,$numPointings |\
	                awk -F "," '{printf "%26s %16s %7s %7s %8s %24s  %02d:%02d:%06.3f %3.0f:%02d:%05.2f %3d", \
                        $1,$2,$3,$4,$5,$6,($7+$9)/15, (($7+$9)/15)%1*60, (($7+$9)*4)%1*60, int(($8+$10))+($8+$10)/1000000, \
                        (($8+$10)<0?-($8+$10):($8+$10))*60%60, (($8+$10)<0?-($8+$10):($8+$10))*3600%60, $11}'
                i=0
                while [ $i -lt $k ]; do
                    echo ${spw[$i]},${bw[$i]},${nChan[i]} |awk -F "," '{printf " %7.2f %5.3f %4.0f", $1,$2,$3}'
                    (( i++ ))
                done
                echo"" |awk '{printf "\n"}'
            fi
        fi 
    done
    rm temporaryCommand.sh
    rm setPartIds.tmp
    rm setBandWidth.sh
    rm setSkyFreq.sh
    rm setSpecChan.sh  > /dev/null 2>&1
    rm tempLatitudes.txt  > /dev/null 2>&1
    rm tempLongitudes.txt  > /dev/null 2>&1
    rm tempRectangle.txt  > /dev/null 2>&1
done
