import json
import jinja2
from snprocess.qc.model import plink


def make_bed(inDir, inFile):
    """Convert SNP file to binary format. Return name of binary file."""
    inFileLink = inDir + inFile
    plink(" --file {} --make-bed --out {}".format(inFileLink, inFileLink))


def md(output_path):
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=jinja2.select_autoescape(['html', 'xml']), )
    
    temp = template_env.get_template("report_template.html")
    data = json.load(open("snprocess/context.json"))
    output_path.write_text(temp.render(data))