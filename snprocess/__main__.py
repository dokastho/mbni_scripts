"""Run all scripts on all phases"""
import pathlib
from snprocess.qc.qc_1 import QC_1
from snprocess.qc.qc_2 import QC_2
from snprocess.model import make_bed, md, printdict
import click
import json
import pathlib
import glob
import os


@click.command()
@click.argument('settings', type=click.STRING)
@click.option('--example','-e', is_flag=True, help='Print an example settings JSON')
def main(settings, example):
    """
    Run all scripts on input supplied by json config file specified by SETTINGS
    """
    FAIL = '\033[91m'
    OKGREEN = '\033[92m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

    # check that plink is installed
    plink_binary = glob.glob("/usr/bin/*")
    if 'plink' not in plink_binary:
        exit(FAIL + "Plink not installed. Download it here:\nhttps://www.cog-genomics.org/plink/1.9/" + ENDC)

    example_path = os.path.dirname(os.path.realpath(__file__))
    reqd = dict(json.load(open(example_path + "/example.json")))

    if example:
        print(printdict(reqd))
        return 0

    try:
        settings = json.load(open(settings))
    except:
        exit(FAIL + "Settings JSON does not exist.\nPrint an example settings JSON using 'snprocess -e'" + ENDC)

    try:
        outdir = settings['outDir']
    except:
        exit(FAIL + "Output dir parameter missing from settings JSON.\nPrint an example settings JSON using 'snprocess -e'" + ENDC)
    o = pathlib.Path(outdir)
    if not o.exists():
        os.makedirs(o)
    # don't clobber existing output if not empty
    else:
        if len(glob.glob(outdir + "*")) > 0:
            exit(FAIL + "Output directory is not empty")

    # check that all parameters are satisfied in the input file, without extras
    s = dict(settings)
    reqd = set(reqd.keys())
    for param in s.keys():
        if param not in reqd:
            exit(FAIL + "Extra parameter in settings JSON: {}.\n\nPrint an example settings JSON using 'snprocess -e'".format(param) + ENDC)
        reqd.remove(param)
    if len(reqd) != 0:
        if len(reqd) == 1:
            exit(
                FAIL + "Parameter missing from settings JSON: {}.\n\nPrint an example settings JSON using 'snprocess -e'".format("".join(reqd)) + ENDC)
        else:
            misslist = ", ".join(reqd)
            exit(FAIL + "Parameters missing from settings JSON: {}.\n\nPrint an example settings JSON using 'snprocess -e'".format(misslist) + ENDC)

    input = settings['fileroute'] + settings['inDir']

    inputFile = input + settings['inFile']

    flist = glob.glob(inputFile + "*")

    binary = True
    if len(flist) == 0:
        exit(FAIL + "Input files {}* not found in {}".format(settings['inFile'], input) + ENDC)
    else:
        for fl in flist:
            if fl[-3:] == "bim":
                binary = True
                break
            binary = False

    if not binary:
        make_bed(input, settings['inFile'])

    print(OKGREEN + BOLD + "Starting QC..." + ENDC)
    markup = QC_1(settings)
    markup = QC_2(settings, markup)

    markup["settings"] = {}

    for item, val in settings.items():
        markup["settings"][item] = val

    json.dump(markup, open("{}/context.json".format(outdir), "w"), indent=4)
    op = pathlib.Path(outdir)
    md(op/"report.html")
    OKGREEN = '\033[92m'
    print(OKGREEN + "SNProcess has finished QC successfully!\nOutput files can be found in{}\n\nA summary is provided in the file found at {}report.html".format(outdir, outdir))


if __name__ == "__main__":
    main()
