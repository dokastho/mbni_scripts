"""First step in data handling."""

from os import mkdir
from os.path import join
import pathlib
from statistics import mean, stdev
from snprocess.qc.model import plink, read_snp_data, clean
from snprocess.qc.model import read_from_output as read
from snprocess.qc.model import run_command as bash
import snprocess.graph as g
import pandas as pd


def QC_1(verbose, opts, phase, inDir):
    """
    Handle data from /PRS/phase3/scripts/QC_1.sh.
    inDir: input files directory, relative link
    outDir: input files directory, relative link
    inFile: format for input file
    """

    data = {
        "phase": phase,
        "graphs": []
    }

    inFile = inDir + opts['inFile']
    # outDir = opts['fileroute'] + opts['outDir']
    outDir = opts['outDir'] + "Phase{}/".format(phase)

    o = pathlib.Path(outDir)
    if not o.exists():
        o.mkdir()

    ####################################################
    # STEP 1: check missingness and generate plots
    plink(" --bfile {} --missing --out {}plink".format(inFile, outDir))

    imiss = read_snp_data(outDir, "plink.imiss", head=0)
    lmiss = read_snp_data(outDir, "plink.lmiss", head=0)
    g.hist_miss(imiss, lmiss, outDir)

    data['graphs'] = data['graphs'] + [
        {
            "name": "Histogram individual missingness",
            "file": outDir + "Hist-individualMissingness.png"
        },
        {
            "name": "Histogram SNP missingness",
            "file": outDir + "Hist-snpMissingness.png"
        }
    ]
    # bash("/usr/bin/Rscript --no-save hist_miss.R {}plink.imiss {}plink.lmiss {}".format(outDir,outDir,outDir))

    ####################################################
    # STEP 2: remove individuals with high missingness.. They recommend using a less stringent filter and then following it with a more stringent filter. Even the more stringent filter is more relaxed than Srijan's
    # Also, they filter on SNP missingness and indivudal missingness. Srijan first filters on individual missingness and then on SNPs much later

    # filter SNPs at 0.01
    plink(" --bfile {} --geno {} --make-bed --out {}plink".format(inFile,
          opts['geno'], outDir))

    # filter individuals at 0.05
    plink(" --bfile {}plink --mind {} --make-bed --out {}plink".format(outDir,
          opts['mind'], outDir))

    ####################################################
    # STEP 3: sexcheck
    plink(" --bfile {}plink --check-sex --out {}plink".format(outDir, outDir))

    # visualize the sex check
    sc = read_snp_data(outDir, "plink.sexcheck", head=0)
    g.sexcheck(sc, outDir)
    # bash("/usr/bin/Rscript --no-save {}sex_check.R {}plink.sexcheck {}".format(outDir, outDir, outDir))
    data['graphs'] = data['graphs'] + [
        {
            "name": "Gender Sexcheck",
            "file": outDir + "Gender_check.png"
        },
        {
            "name": "Male Sexcheck",
            "file": outDir + "Men_check.png"
        },
        {
            "name": "Female Sexcheck",
            "file": outDir + "Women_check.png"
        }
    ]

    # remove individuals with problematic sex
    output = bash('grep PROBLEM {}plink.sexcheck'.format(outDir))
    output = read(output, 'PROBLEM')
    sd_df = pd.DataFrame({0: output[0], 1: output[1]})
    sd_df.to_csv(sep="\t", path_or_buf='{}sex_discrepency.txt'.format(
        outDir), index=False)

    # bash('awk \'{{print $1, $2}}\' awkout.txt > {}sex_discrepency.txt'.format(outDir))

    plink(" -bfile {}plink --remove {}sex_discrepency.txt --make-bed --out {}plink".format(outDir, outDir, outDir))

    # impute sex... (not sure why this is necessary). NOT RUNNING IT
    # plink -bfile ${outFile}_5 --impute-sex --make-bed --out ${outFile}_6

    ####################################################
    # STEP 4: select autosomal SNPs only an filter out SNPs with low minor allele frequency (MAF)

    # select autosomal SNPs only, ie from chr 1 to 22
    # bash("awk '{ if ($1 >= 1 && $1 <= 22) print $2 }' plink.bim > {}snp_1_22.txt".format(outDir))
    output = read_snp_data(outDir, "plink.bim")
    output = output[1][(output[0] >= 1) & (output[0] <= 22)]
    output.to_csv(sep="\t", path_or_buf='{}snp_1_22.txt'.format(
        outDir), index=False)

    plink(" --bfile {}plink --extract {}snp_1_22.txt --make-bed --out {}plink".format(outDir, outDir, outDir))

    # generate plot of MAF distribution
    plink(" --bfile {}plink --freq --out {}MAF_check".format(outDir, outDir))

    # visualize it

    frq = read_snp_data(outDir, "MAF_check.frq", head=0)
    g.maf_check(frq, outDir)
    data['graphs'].append({
        "name": "MAF Distribution",
        "file": outDir + "MAF_distribution.png"
    })
    # bash("/usr/bin/Rscript --no-save MAF_check.R {}MAF_check. {}".format(outDir, outDir))

    # remove SNPs with low MAF... major point of diversion. Srijan's MAF filtering crieria is VERY small. 0.005 vs what they recommend here of 0.05. I'll go midway with 0.01.
    # maf filter at 0.005
    plink(" --bfile {}plink --maf {} --make-bed --out {}plink".format(outDir,
          opts['maf'], outDir))

    ####################################################
    # STEP 5: Delete SNPs not in the Hardy-WEinberg equilibrium (HWE)

    plink(" --bfile {}plink --hardy --out {}plink".format(outDir, outDir))

    # select SNPs with HWE p-value below 0.00001
    # bash("awk '{ if ($9 < 0.0001) print $0 }' {}.hwe > {}zoomhwe.hwe".format(outFile, outDir))
    output = read_snp_data(outDir, "plink.hwe", head=0)
    # output = output[output.columns[0]][(output[output.columns[8]] < .0001)]
    # TODO question about data table
    output = output[(output[output.columns[8]] < .0001)]
    output.to_csv(sep="\t", path_or_buf='{}zoom.hwe'.format(
        outDir), index=False)

    hwe_df = read_snp_data(outDir, "plink.hwe", head=0)
    zoom = read_snp_data(outDir, "zoom.hwe", head=0)
    g.hwe(hwe_df, zoom, outDir)

    data['graphs'] = data['graphs'] + [
        {
            "name": "Histogram HWE",
            "file": outDir + "HWE_Histogram.png"
        },
        {
            "name": "Histogram HWE: strongly deviating SNPs only",
            "file": outDir + "HWE_below_theshold_Histogram.png"
        }
    ]

    # bash("/usr/bin/Rscript --no-save hwe.R plink.hwe {}zoom.hwe {}foo".format(outDir,outDir))

    # now delete them. We don'd have cae / controls, so filter all at 1e-10
    # this is again a departure from Yu's pipeline as they filter at 1e-6
    # plink --bfile ${outFile}_7 --hwe 1e-6 --make-bed --out ${outFile}_8
    plink(" --bfile {}plink --hwe 1e-10 --hwe-all --make-bed --out {}plink".format(outDir, outDir))

    ############################################################
    # STEP 6: Heterozygosity and LD Pruning

    # so first with heterzygosity rate. Remove individuals with a heterozygosity rate of more than 3 sd from the mean
    # heterozygosity: carrying two different alleles of a SNP. Low indicates inbreeding, high indicates low samples quality
    # exclude inversion regions (high LD regions).
    # Linkage Disequilibrium (LD) a measure of non-random association between alleles at different loci in the same chromosome.
    # SNPs are in LD when the frequency of association of their alleles is higher than expected under random assortment.
    # To calculate LD, we use the following parameters: window size=50, shift size=5, pairwise SNP-SNP r^2 metric=0.2
    # Yu's parameters are 100, 25, 0.5. Given the small sample sizes we are dealing with, Yu's parameters, particularly for r^2
    # make more sense. More SNPs would be excluded with r^2=0.2

    plink(" --bfile {}plink --indep-pairwise {} {} {} --out {}indepSNP".format(outDir,
          opts['indep_pairwise'][0], opts['indep_pairwise'][1], opts['indep_pairwise'][2], outDir))

    # get the pruned data set
    plink(" --bfile {}plink --extract {}indepSNP.prune.in --het --out {}R_hetCheck".format(outDir, outDir, outDir))

    # plot the heterogygosity rate
    df = read_snp_data(outDir, "R_hetCheck.het", head = 0)
    g.heterozygosity_rate(df, outDir)

    data['graphs'].append({
        "name": "Heterozygosity Rate",
        "file": outDir + "heterozygosity.png"
    })
    # bash("/usr/bin/RScript --no-save heterogygosity_rate.R {}R_hetCheck {}".format(outDir, outDir))

    # list the individuals more than 3 sd away from the heterozygosity rate mean.
    tbl = join(outDir + "fail-het-qc.txt")

    df["HET_RATE"] = (df['N(NM)'] - df['O(HOM)']) / df['N(NM)']

    het_fail: pd.DataFrame
    het_fail = df[df['HET_RATE'] < mean(df['HET_RATE']) - 3 * stdev(df['HET_RATE'])]
    het_fail.append(df[df['HET_RATE'] > mean(df['HET_RATE']) + 3 * stdev(df['HET_RATE'])])
    het_fail['HET_DST'] = (het_fail['HET_RATE'] -
                           mean(df['HET_RATE']) / stdev(df['HET_RATE']))
    het_fail.to_csv(tbl)
    # bash("/usr/bin/Rscript --no-save heterozygosity_outliers.R {}R_hetCheck {}".format(outDir, outDir))

    # need to exclude these individuals from the analysis.
    # TODO
    # bash('''sed 's/"// g' {}fail-het-qc.txt | awk '{print $1, $2}' > {}het-fail-ind.txt'''.format(outDir, outDir))

    # plink(" --bfile plink --remove {}het-fail-ind.txt --make-bed".format(outDir))

    ############################################################
    # STEP 7: Relatedness

    # This step isn't there in Yu's workflow, because it shouldn't really be necessary.
    # relatedness @0.2
    plink(" --bfile {}plink --extract {}indepSNP.prune.in --genome --min {} --out {}pihat_min0.2".format(
        outDir, outDir, opts['relatedness'], outDir))

    # visualize relations. But there will be none! or should be none!
    # bash("awk '{ if ($8 > 0.9) print $0}' {}pihat_min0.2.genome > {}zoom_pihat.genome".format(outDir, outDir))
    output = read_snp_data(outDir, "pihat_min0.2.genome", head=0)
    output = output[output.columns[0]][(output[output.columns[7]] > 0.9)]
    output.to_csv(sep="\t", path_or_buf='{}zoom_pihat.genome'.format(
        outDir), index=False)

    # TODO
    # bash("/usr/bin/Rscript --no-save relatedness.R {}pihat_min0.2.genome {}zoom_pihat.genome {}".format(outDir, outDir, outDir))

    clean(outDir)
    return data
