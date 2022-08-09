VPATH:=images
TARGETS:=main.pdf
LATEXEC:=rubber --pdf main.tex
IMAGES:= 
TEX:=main.tex biblio.bib  info.tex intro.tex proposal.tex schedule.tex

export

default: $(TARGETS)

main.pdf : $(TEX) $(IMAGES)
	-$(LATEXEC)

clean:
	-$(LATEXEC) --clean

.PHONY: clean default
