# Summary
command-line tool to extract images from a pdf, respecting softmask if present and compositing onto a background color of choice

# Requires
- Python 3
- PyPDF3+
- pillow

prolly easiest to install those in a conda env since they have C library dependencies:
```
conda install pypdf
conda install pillow
```