# Summary
command-line tool to extract images from a pdf, respecting softmask if present and compositing onto a background color of choice

# Requires
PyPDF2
PIL

prolly easiest to install those in a conda env since they have C library dependencies

# Caveats
I only tested this with the pdfs I was trying to extract from (RPG books). The code prolly makes some bad assumptions or misses some weird combinations of data orientations that weren't present in my pdfs. which is to say this might require modification for more general use.

