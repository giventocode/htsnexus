#!/bin/bash
#
# script to run variant calling in ONE region (used by parallel in main.sh)

JOB="$1"
JOBS="$2"
export REGION="$3"
export SERVER="$4"
export NAMESPACE="$5"
shift 5

set -e -o pipefail

# For each sample/"read group set" ID, use the htsnexus client to fetch a BAM
# slice covering the desired region.
fetch() {
    # this subroutine is invoked below by parallel which is used here just for
    # retry logic.
    htsnexus -r "$REGION" -s "$SERVER" "$NAMESPACE" "$1" > "$2"
}
export -f fetch
SECONDS=0
bams=()
for id in "$@"; do
    bamfn=$(mktemp "${REGION}-${id}-XXXXXX.bam")
    # use parallel to call fetch with retry
    parallel --retries 3 fetch "$id" "$bamfn" ::: 0
    bams+=("$bamfn")
    # index the BAM slice -- this is unnecessary except to suppress an annoying
    # stderr warning from freebayes
    samtools index "$bamfn" &
done
T_FETCHING=$SECONDS
wait
bams_size=$(du -ch --apparent-size ${bams[@]} | tail -n1 | cut -f1)

# run freebayes on the BAM slices
SECONDS=0
freebayes --standard-filters --min-repeat-entropy 1 --no-partial-observations --min-alternate-fraction 0.1 \
    -f hs37d5.fa --region "$REGION" ${bams[@]}
>&2 echo "(${JOB}/${JOBS}) $REGION fetched ${bams_size} in ${T_FETCHING}s, freebayes took ${SECONDS}s"

rm ${bams[@]}

