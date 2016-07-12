#!/usr/bin/env python2.7

# This utility takes an htsnexus index database generated by one of the
# htsnexus_index_{bam,cram,vcf} utilities (and possibly downsampled) and adds
# a 'seqBin' column to the block index (htsfiles_blocks). This is populated
# with a bin number reflecting the (seqLo,seqHi] range, or null if seq is
# null. Lastly, a (_dbid,seq,seqBin) index is added to htsfiles_blocks.
#
# The server requires the index database to have this bin index, to facilitate
# efficient genomic range lookup.
#
# We'd really rather have seqBin as a materialized view instead of requiring
# this transformation, but SQLite does not support that. 

import argparse
import sys
import sqlite3
import shutil

parser = argparse.ArgumentParser(description='htsnexus index bin indexing utility')
parser.add_argument('db', type=str, help="database file (will be modified in-place)")
args = parser.parse_args()

# open the destination database and open a transaction
conn = sqlite3.connect(args.db)
cursor = conn.cursor()

# add the seqBin column
cursor.execute('alter table htsfiles_blocks add column seqBin integer check(seq is null or (seqBin is not null and seqBin >= 0 and seqBin < 69905))')

# populate it
cursor.execute("""
update htsfiles_blocks
set seqBin =
    case
        when (seqLo>>14) = (seqHi>>14) then (seqLo>>14)+1+16+256+4096
        when (seqLo>>18) = (seqHi>>18) then (seqLo>>18)+1+16+256
        when (seqLo>>22) = (seqHi>>22) then (seqLo>>22)+1+16
        when (seqLo>>26) = (seqHi>>26) then (seqLo>>26)+1
        else 0
    end
where seqLo not null and seqHi not null
""")

# add the index
cursor.execute('create index htsfiles_blocks_bin_index on htsfiles_blocks(_dbid,seq,seqBin)')

# finish up
conn.commit()
conn.execute('vacuum')
