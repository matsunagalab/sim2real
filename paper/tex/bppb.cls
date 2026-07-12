%%
%%% bppb.cls for (u)pLaTeX2e+LuaLaTeX+pdflatex
%%   for the Biophysics and Physicobiology of the biophysical society of Japan
%%     by Motoaki Sato (ULS and Company), 2022
%%     E-mail: teppei@uls.co.jp, http://www.uls.co.jp/
%%% logo of cc (bppb_cc.pdf) is deleted
%%
\NeedsTeXFormat{LaTeX2e}[1995/12/01]
\ProvidesClass{bppb}
  [2022/04/18 v1.0 for the Biophysics and Physicobiology]

\def\bppb@warning{\ClassWarningNoLine{bppb}}
%\def\bppbline@warning{\ClassWarning{bppb}}

\newif\if@Proof \@Prooffalse
\DeclareOption{Proof}{\@Prooftrue}

\newcommand\@ptsize{}
\newif\if@restonecol
%\newif\if@titlepage
%\@titlepagefalse
\DeclareOption{a4paper}
 {\setlength\paperheight {297mm}%
  \setlength\paperwidth  {210mm}}
\DeclareOption{10pt}{\renewcommand\@ptsize{0}}
%\DeclareOption{11pt}{\renewcommand\@ptsize{1}}
%\DeclareOption{12pt}{\renewcommand\@ptsize{2}}
\DeclareOption{oneside}{\@twosidefalse \@mparswitchfalse}
\DeclareOption{twoside}{\@twosidetrue  \@mparswitchtrue}
\DeclareOption{draft}{\setlength\overfullrule{5pt}}
\DeclareOption{final}{\setlength\overfullrule{0pt}}
%\DeclareOption{titlepage}{\@titlepagetrue}
%\DeclareOption{notitlepage}{\@titlepagefalse}
\DeclareOption{onecolumn}{\@twocolumnfalse}
\DeclareOption{twocolumn}{\@twocolumntrue}
\DeclareOption{leqno}{\input{leqno.clo}}
\DeclareOption{fleqn}{\input{fleqn.clo}}
\DeclareOption{openbib}{%
  \AtEndOfPackage{%
    \renewcommand\@openbib@code{%
      \advance\leftmargin\bibindent
      \itemindent -\bibindent
      \listparindent \itemindent
      \parsep \z@
      }%
    \renewcommand\newblock{\par}}%
}
\ExecuteOptions{a4paper,10pt,twoside,onecolumn,final}
\ProcessOptions

%\input{size1\@ptsize.clo}
\renewcommand{\normalsize}{%
 \@setfontsize\normalsize\@xpt\@xiipt % 12pt
 \abovedisplayskip1\baselineskip \@plus.25\baselineskip \@minus.15\baselineskip
 \abovedisplayshortskip\z@ \@plus.15\baselineskip
 \belowdisplayshortskip.6\baselineskip
  \@plus.15\baselineskip \@minus.1\baselineskip
 \belowdisplayskip \abovedisplayskip
 \let\@listi\@listI}

\normalsize
\ifx\MakeRobust\@undefined \else
    \MakeRobust\normalsize
\fi
\DeclareRobustCommand\small{%
 \@setfontsize\small\@ixpt{11}%??
 \abovedisplayskip1\baselineskip \@plus.25\baselineskip \@minus.15\baselineskip
 \abovedisplayshortskip\z@ \@plus.15\baselineskip
 \belowdisplayshortskip.6\baselineskip
  \@plus.15\baselineskip \@minus.1\baselineskip
 \belowdisplayskip \abovedisplayskip
 \def\@listi{\leftmargin\leftmargini
             \topsep 4\p@ \@plus2\p@ \@minus2\p@
             \parsep 2\p@ \@plus\p@ \@minus\p@
             \itemsep \parsep}%
}
\DeclareRobustCommand\footnotesize{%
 \@setfontsize\footnotesize\@viiipt{9.5}%??
 \abovedisplayskip1\baselineskip \@plus.25\baselineskip \@minus.15\baselineskip
 \abovedisplayshortskip\z@ \@plus.15\baselineskip
 \belowdisplayshortskip.6\baselineskip
  \@plus.15\baselineskip \@minus.1\baselineskip
 \belowdisplayskip \abovedisplayskip
 \def\@listi{\leftmargin\leftmargini
             \topsep 3\p@ \@plus\p@ \@minus\p@
             \parsep 2\p@ \@plus\p@ \@minus\p@
             \itemsep \parsep}%
}
\DeclareRobustCommand\scriptsize{\@setfontsize\scriptsize\@viipt\@viiipt}
\DeclareRobustCommand\tiny{\@setfontsize\tiny\@vpt\@vipt}
\DeclareRobustCommand\large{\@setfontsize\large\@xiipt{14}}
\DeclareRobustCommand\Large{\@setfontsize\Large\@xivpt{18}}
\DeclareRobustCommand\LARGE{\@setfontsize\LARGE\@xviipt{22}}
\DeclareRobustCommand\huge{\@setfontsize\huge\@xxpt{25}}
\DeclareRobustCommand\Huge{\@setfontsize\Huge\@xxvpt{30}}

\setlength\parindent{10\p@}

\setlength\smallskipamount{3\p@ \@plus 1\p@ \@minus 1\p@}
\setlength\medskipamount{6\p@ \@plus 2\p@ \@minus 2\p@}
\setlength\bigskipamount{12\p@ \@plus 4\p@ \@minus 4\p@}

\headheight10\p@
\headsep14\p@ % OK
\topskip10\p@
\footskip15.5mm % OK
\maxdepth.5\topskip
\textwidth170mm % 482\p@
%\@settopoint\textwidth
\textheight53\baselineskip
\advance \textheight \topskip
\advance \textheight .1mm
%% 210x297
\topmargin30.2mm % OK
\advance \topmargin -1in
%\@settopoint\topmargin
\oddsidemargin20mm
\advance \oddsidemargin -1in
%\@settopoint\oddsidemargin
\evensidemargin\oddsidemargin
%\@settopoint\evensidemargin

\setlength\footnotesep{8.4\p@}

\setlength{\skip\footins}{9\p@ \@plus 4\p@ \@minus 2\p@}

\floatsep .5\baselineskip \@plus 2\p@ \@minus 2\p@
\dblfloatsep .5\baselineskip \@plus 2\p@ \@minus 2\p@
\textfloatsep 1.5\baselineskip \@plus 2\p@ \@minus 4\p@
\dbltextfloatsep 1.5\baselineskip \@plus 2\p@ \@minus 4\p@
\intextsep 1.5\baselineskip \@plus 2\p@ \@minus 2\p@

\setlength\@fptop{0\p@ \@plus 1fil}
\setlength\@fpsep{8\p@ \@plus 2fil}
\setlength\@fpbot{0\p@ \@plus 1fil}
\setlength\@dblfptop{0\p@ \@plus 1fil}
\setlength\@dblfpsep{8\p@ \@plus 2fil}
\setlength\@dblfpbot{0\p@ \@plus 1fil}
\setlength\partopsep{2\p@ \@plus 1\p@ \@minus 1\p@}
\def\@listi{\leftmargin\leftmargini
            \parsep 4\p@ \@plus2\p@ \@minus\p@
            \topsep 8\p@ \@plus2\p@ \@minus4\p@
            \itemsep4\p@ \@plus2\p@ \@minus\p@}
\let\@listI\@listi
\@listi
\def\@listii {\leftmargin\leftmarginii
              \labelwidth\leftmarginii
              \advance\labelwidth-\labelsep
              \topsep    4\p@ \@plus2\p@ \@minus\p@
              \parsep    2\p@ \@plus\p@  \@minus\p@
              \itemsep   \parsep}
\def\@listiii{\leftmargin\leftmarginiii
              \labelwidth\leftmarginiii
              \advance\labelwidth-\labelsep
              \topsep    2\p@ \@plus\p@\@minus\p@
              \parsep    \z@
              \partopsep \p@ \@plus\z@ \@minus\p@
              \itemsep   \topsep}
\def\@listiv {\leftmargin\leftmarginiv
              \labelwidth\leftmarginiv
              \advance\labelwidth-\labelsep}
\def\@listv  {\leftmargin\leftmarginv
              \labelwidth\leftmarginv
              \advance\labelwidth-\labelsep}
\def\@listvi {\leftmargin\leftmarginvi
              \labelwidth\leftmarginvi
              \advance\labelwidth-\labelsep}
%% End of file `size10.clo'.

\setlength\lineskip{1\p@}
\setlength\normallineskip{1\p@}
\renewcommand\baselinestretch{}
\parskip\z@

\@lowpenalty   51
\@medpenalty  151
\@highpenalty 301

\setcounter{topnumber}{4}% 2
\setcounter{bottomnumber}{4}% 1
\setcounter{totalnumber}{6}% 3
\setcounter{dbltopnumber}{6}% 2
\renewcommand\topfraction{.94}
\renewcommand\bottomfraction{.94}
\renewcommand\textfraction{.06}
\renewcommand\floatpagefraction{.06}
\renewcommand\dbltopfraction{.94}
\renewcommand\dblfloatpagefraction{.06}

\if@Proof
 \def\@Rtop{\rlap{\smash{\rule[-\headsep]{0.05mm}{10mm}%
  \rule[-\headsep]{10mm}{0.05mm}}}}
 \def\@Ltop{\llap{\smash{\rule[-\headsep]{10mm}{0.05mm}%
  \rule[-\headsep]{0.05mm}{10mm}}}}
 \def\@Rbot{\rlap{\smash{\raisebox{1\footskip}% v1.06
  {\rule[-10mm]{0.05mm}{10mm}\rule{10mm}{0.05mm}}}}}
 \def\@Lbot{\llap{\smash{\raisebox{1\footskip}% v1.06
  {\rule{10mm}{0.05mm}\rule[-10mm]{0.05mm}{10mm}}}}}
\else
 \let\@Rtop\relax\let\@Ltop\relax\let\@Rbot\relax\let\@Lbot\relax
\fi

\def\ps@empty{%
 \let\@mkboth\@gobbletwo
 \def\@oddhead{\@Ltop\hfil\@Rtop}%
 \let\@evenhead\@oddhead
 \def\@oddfoot{\@Lbot\hfil\@Rbot}%
 \let\@evenfoot\@oddfoot
}

\def\ps@plain{%
 \let\@mkboth\@gobbletwo
 \def\@oddhead{\@Ltop\hfil\@Rtop}%
 \let\@evenhead\@oddhead
 \def\@oddfoot{\@Lbot\hfil
  e\@Vol\@bppbdoi\_\thepage\@Rbot}%
 \let\@evenfoot\@oddfoot
}

\def\Vol#1{% Vol.19 = Year 2022
 \def\@tempa{#1}%
 \ifx\@tempa\@empty
  \gdef\@Vol{xx}\gdef\@Year{20XX}%
 \else
  \edef\@tempb{\zap@space#1 \@empty}%
  \afterassignment\remove@to@nnil
   \count@ 0\@tempb\relax\@nnil
  \ifnum\count@=\z@
   \gdef\@Vol{xx}%
  \else
   \@tempcnta=#1\relax
   \advance \@tempcnta 2003\relax
   \xdef\@Year{\the\@tempcnta}%
   \gdef\@Vol{\zap@space#1 \@empty}%
  \fi
 \fi
}
\def\@Vol{00}%
\def\@Year{20XX}

\def\ps@headings{%
 \def\@oddfoot{\@Lbot\hfil
  e\@Vol\@bppbdoi\_\thepage\@Rbot}%
 \let\@evenfoot\@oddfoot
 \def\@oddhead{\@Ltop\hfil\@outputRhead\@Rtop}% \hskip10\p@\thepage
 \def\@evenhead{\@Ltop Biophysics and Physicobiology\hskip1ex %OK
  Vol.\,\@Vol\hfil\@Rtop}% \thepage\hskip10\p@
}

%% <authorlist, (C)authorentry>
\newtoks\@authorlist
\newcount\@authorcnt
\newcount\@alcnt
\newcount\total@nr

\def\authorlist#1{%
 \@authorlist={#1}\the\@authorlist
 \global\fn@alcnt\z@
}

\def\authorentry{\@ifnextchar[% ]
 {\bppb@ae}{\bppb@ae[]}%
}
\def\Cauthorentry{\@ifnextchar[% ]
 {\bppb@Cae}{\bppb@Cae[]}%
}

\newif\if@bppbnote \@bppbnotefalse
\DeclareRobustCommand{\Note}{\global\@bppbnotetrue}

\def\bppb@ae[#1]#2#3{%
 \def\tmp@authname{#2}%
 \ifx\tmp@authname\@empty
  \bppb@warning{Author's name is not specified}%
 \else
  \@tempcnta\z@
  \global\advance \@authorcnt \@ne
  %% author label
  \get@al{#3}%
  %% author's name
  %\@temptokena{#2}%
  %\def\tmp@name##1 ##2\@nil{##1 \protect\textsc{##2}}%
  %\protected@edef\fmt@authorname{%
  %  \expandafter\tmp@name\the\@temptokena\@nil}%
  \setbox0\hbox{#2}\setbox\z@\box\voidb@x
  \expandafter\protected@xdef\csname @authorname\number\@authorcnt\endcsname{%
   %\fmt@authorname
   \ignorespaces #2\unskip\kern\z@\protect\save@affi{\plural@affi}%
   \if@bppbnote $^{*}$\fi
  }%
  \global\@bppbnotefalse
  %% author's name for header
  \ifnum\@authorcnt<\thr@@
   \def\tmp@headname{#1}%
   \ifx\tmp@headname\@empty
    \def\get@Sname##1 ##2\@nil{##2}%
    \protected@edef\fmt@headauthor{\get@Sname #2\@nil}%
    \expandafter
     \protected@xdef\csname @Hauthorname\number\@authorcnt\endcsname{%
      \fmt@headauthor}%
   \else
    \expandafter
     \protected@xdef\csname @Hauthorname\number\@authorcnt\endcsname{%
      \tmp@headname}%
   \fi
  \fi
  %%
  \global\total@nr\@authorcnt
  \def\plural@affi{}%
 \fi
}

\newcount\fn@alcnt
\def\bppb@Cae[#1]#2#3#4#5{%
 \bppb@ae[#1]{#2}{#3}%
  %% #1 #2 #4 #5
  %% authorname of Cauthorentry
  \def\SI@authname{#1}%
  \ifx\SI@authname\@empty
   \global\advance \fn@alcnt \@ne
   \expandafter\protected@xdef
    \csname fn@authorname\number\fn@alcnt\endcsname{\ignorespaces #2\unskip, }%
  \else
   \global\advance \fn@alcnt \@ne
   \expandafter\protected@xdef
    \csname fn@authorname\number\fn@alcnt\endcsname{\ignorespaces #1\unskip, }%
  \fi
  %% ORCID iD
  \def\tmp@orcid{#4}%
  \def\tmp@email{#5}%
  \ifx\tmp@orcid\@empty
  \else
   \expandafter\protected@xdef\csname fn@orcid\number\fn@alcnt\endcsname{%
    ORCID iD: \protect\href{#4}{\protect\bppb@email{#4}}%
    \ifx\tmp@email\@empty\else, \fi}% 
  \fi
  %% e-mail
  \ifx\tmp@email\@empty\else
   \expandafter\protected@xdef\csname fn@email\number\fn@alcnt\endcsname{%
    e-mail:\ \protect\bppb@email{#5}}%
  \fi
}

\def\@outputRhead{% 
 \ifnum\total@nr=\@ne
  \csname @Hauthorname1\endcsname\unskip
 \else
  \ifnum\total@nr=\tw@
   \csname @Hauthorname1\endcsname\unskip\ and 
   \csname @Hauthorname2\endcsname\unskip
  \else
   \csname @Hauthorname1\endcsname\unskip\ et al.%
  \fi
 \fi
 \if@outputrunningtitle: \head@title\fi
}

\def\get@al#1{%
 %%\def\al@none{none}
 %%\def\@tempaffi{#1}%
 %%\ifx\al@none\@tempaffi\else
  \@for\get@label:=#1\do{%
   \@ifundefined{al@\get@label}%
    {%
     \global\advance \@alcnt \@ne
     \expandafter\xdef\csname al@\get@label\endcsname{\the\@alcnt}%
     \global\advance \@tempcnta \@ne
     \protected@xdef\plural@affi{\plural@affi
      \ifnum\@tempcnta=\@ne
       $^{\csname al@\get@label\endcsname}$%
      \else
       $^{,\csname al@\get@label\endcsname}$%
      \fi
     }%
     %% author label check <-> (C)affiliate
     \protected@xdef\save@authorlabel{\save@authorlabel
      \ifnum\@alcnt=\@ne\else,\fi \get@label}%
    }%
    {%
     \global\advance \@tempcnta \@ne
     \protected@xdef\plural@affi{\plural@affi
      \ifnum\@tempcnta=\@ne
       $^{\csname al@\get@label\endcsname}$%
      \else
       $^{,\csname al@\get@label\endcsname}$%
      \fi
     }%
    }%
  }%
 %%\fi
}
\def\plural@affi{}
\def\save@affi#1{#1}
\def\save@authorlabel{}

\def\affiliate[#1]#2{%
 \@ifundefined{al@#1}%
  {\expandafter\def\csname al@#1\endcsname{?}% ((
   \bppb@warning{Check the "#1" label of \string\(C)affiliate, 
    it is not assigned by \string\(C)authorentry}%
  }{}%
 %% check label of (C)affiliate
 %%\expandafter\gdef\csname chkaffi@#1\endcsname{}%
 \@ifundefined{chkaffi@#1}%
  {\expandafter\gdef\csname chkaffi@#1\endcsname{}}%
  {}
 %%
 \@ifundefined{affi@al@#1}{%
  \expandafter\gdef\csname affi@al@#1\endcsname{}%
  \protected@xdef\@affiliate{\@affiliate
   \protect\save@affi{%
    $^{\mbox{\scriptsize\itshape 
     \csname al@#1\endcsname}}$\ 
   }%
   #2\par
  }%
 }{}%
}
\def\@affiliate{}

\def\Caffiliate[#1]#2#3{%
 \affiliate[#1]{#2}%
 %%
 \def\tmp@fulladdress{#3}%
 \ifx\tmp@fulladdress\@empty
  \def\bppb@fulladdress{#2\unskip}%
 \else
  \def\bppb@fulladdress{#3\unskip}%
 \fi
 \global\advance \fn@alcnt \@ne
 \protected@xdef\save@foot@affiliate{%
  \ifnum\fn@alcnt=\@ne
   \csname fn@authorname\number\fn@alcnt\endcsname
   \bppb@fulladdress. 
   \csname fn@orcid\number\fn@alcnt\endcsname
   \csname fn@email\number\fn@alcnt\endcsname
  \else
   \save@foot@affiliate
   \unskip; 
   \csname fn@authorname\number\fn@alcnt\endcsname
   \bppb@fulladdress\unskip. 
   \csname fn@orcid\number\fn@alcnt\endcsname
   \csname fn@email\number\fn@alcnt\endcsname
  \fi
 }%
}
\def\save@foot@affiliate{}

\def\output@foot@affiliate{%
 \ifnum\fn@alcnt=\z@\else
  \footnotetext{\normalsize
  %%\ifx\@bppbnote\@empty\rule{0mm}{3.8mm}\fi
  Corresponding author%
  \ifnum\fn@alcnt=\@ne\else s\fi
  : \save@foot@affiliate}%
 \fi
}

\def\breakauthorline#1{%
 \@for\@breakauthor:=#1\do{%
  \expandafter\gdef\csname @breakauthorline\@breakauthor\endcsname{\\}%
 }%
  \@authorcnt=\z@
  \loop\ifnum\@authorcnt<\total@nr
   \advance \@authorcnt \@ne
    \@ifundefined{@breakauthorline\number\@authorcnt}%
     {\expandafter\gdef\csname @breakauthorline\number\@authorcnt\endcsname{%
      \relax}}
     {\relax}%
  \repeat
}

\def\@outputauthorlist{%
 \@authorcnt\z@
 %\@tempcnta\total@nr \advance \@tempcnta -\@ne
 \loop
  \ifnum \@authorcnt < \total@nr
   \advance \@authorcnt \@ne
   \ifnum \@authorcnt < \total@nr %\@tempcnta
    \mbox{\csname @authorname\number\@authorcnt\endcsname\unskip},
    \csname @breakauthorline\number\@authorcnt\endcsname
   \else
    \ifnum \@authorcnt=\total@nr
     \mbox{\csname @authorname\number\@authorcnt\endcsname\unskip}%
     %\csname @breakauthorline\number\@authorcnt\endcsname
     %\ignorespaces
    %\else
    % \mbox{\csname @authorname\number\@authorcnt\endcsname\unskip}\ 
    % \csname @breakauthorline\number\@authorcnt\endcsname
    % %% \ifnum \total@nr=\tw@\ \else , \fi
    % and\  
    \fi
   \fi
 \repeat
}
%% </authorlist, (C)authorentry>

%% <Abbreviations>
\def\Abbreviations#1{\gdef\@Abbreviations{#1}}
\def\@Abbreviations{}
%% </Abbreviations>

%% <@bppbnote>
\def\bppbnote#1{\gdef\@bppbnote{#1}}
\def\@bppbnote{}
%% </@bppbnote>

\newcommand\maketitle{\par
 %% check label of (C)affiliate
 \@for\get@author@label:={\save@authorlabel}\do{%
  \@ifundefined{chkaffi@\get@author@label}{%(
   \bppb@warning{\string\(C)affiliate "\get@author@label" is not specified}%
  }{}%
 }%
 %%
 \ifnum\@alcnt=\@ne
  \let\save@affi\@gobble
 \fi
 %%
 %%\enlargethispage{13mm}%
 \begingroup
  %\renewcommand\thefootnote{\@fnsymbol\c@footnote}%
  %\def\@makefnmark{\rlap{\@textsuperscript{\normalfont\@thefnmark}}}%
  \long\def\@makefntext##1{\parindent\z@
   %\noindent
   % \hb@xt@1.8em{\hss\@textsuperscript{\normalfont\@thefnmark}}
   ##1}%
  %%
  \global\@topnum\z@   % Prevents figures from going at top of page.
  \parindent\z@
  \@maketitle
  \thispagestyle{plain}%
  \ifx\@bppbnote\@empty\else
   \footnotetext{\normalsize $^{\ast}$\@bppbnote}%
  \fi
  \ifx\@Abbreviations\@empty\else
   \footnotetext{\normalsize Abbreviations: \ignorespaces\@Abbreviations}%
  \fi
  \output@foot@affiliate
 \endgroup
 \setcounter{footnote}{0}%
 \global\let\maketitle\relax
 \global\let\@maketitle\relax
 \global\let\@title\@empty
 \global\let\title\relax
 \global\let\@authorlist\@empty
 \global\let\@affiliate\@empty
 \global\let\save@foot@affiliate\@empty
 \global\let\@outputauthorlist\@empty
 \global\let\output@foot@affiliate\@empty
 %\global\let\thanks\relax
 %\global\let\@thanks\@empty
 %\global\let\@author\@empty
 %\global\let\@date\@empty
 %\global\let\author\relax
 %\global\let\date\relax
 %\global\let\and\relax
}

\newdimen\@dimA
\newdimen\@dimB
\newdimen\@dimC

\def\bppbdoi#1{\gdef\@bppbdoi{#1}}
\def\@bppbdoi{0000}

%\def\bppb@page@range{%
% \@ifundefined{r@bppb@lastpage}{\def\bppb@last@page{1}\def\get@lp{1}}%
%  {\edef\exp@lp{\csname r@bppb@lastpage\endcsname}%
%   \edef\get@lp{\expandafter\@cdr\exp@lp\@nil}%
%   \edef\bppb@last@page{\get@lp}%
%  }%
%  \ifnum\get@lp=\c@page
%   \thepage
%  \else
%   \thepage--\bppb@last@page
%  \fi
%}

\def\@make@BPPBhead{%
 \leavevmode
 \hbox to \textwidth{\hss
 \@dimA18.5mm
 \@dimB=\dimexpr \textwidth - 139mm\relax
 \begin{tikzpicture}[inner sep=0pt,outer sep=0pt]%
  \useasboundingbox (0,0) rectangle (\textwidth,\@dimA);
  %\draw (0,0) rectangle (\textwidth,\@dimA);
  %% 20xx THE BIO...
  \@dimC=\dimexpr \@dimA + 2.9mm\relax %OK
  \node [above right] at (0,\@dimC)
   {\textcopyright\ \@Year\ THE BIOPHYSICAL SOCIETY OF JAPAN};
  \@dimC=\dimexpr \@dimC - .7mm\relax  %OK
  \node [above left] at (\textwidth,\@dimC)
   {{\bfseries doi: 10.2142/biophysico.bppb-v\@Vol.\@bppbdoi}};
  \@dimC=\dimexpr \@dimA + 6.3mm\relax %OK
  \node [above left] at (\textwidth,\@dimC)
   {{\bfseries Vol.\,\@Vol, e\@Vol\@bppbdoi\ (\@Year)}}; 
  %%
  \draw [line width=0.4mm] (0,\@dimA) -- (\textwidth,\@dimA);
  \IfFileExists{bppb-logo.pdf}{%
   \@dimC=\dimexpr \@dimA - 1.9mm\relax
   \node [below right] at (0,\@dimC)
    {\includegraphics[scale=0.5816]{bppb-logo.pdf}};
  }{%
   \@dimC=\dimexpr \@dimA - 2.8mm\relax
   \node [below right] at (0,\@dimC) {\rule{25mm}{13.8mm}}; 
  }
  \@dimC=\dimexpr \@dimA - 3.2mm\relax %OK
  \node [below right] at (\@dimB,\@dimC)% 31.9mm
   {\bfseries\fontsize{24pt}{\z@}\selectfont Biophysics and Physicobiology};
  \@dimC=\dimexpr \textwidth - 1.7mm\relax
  \node [above left] at (\@dimC,2mm) %OK
   %{\href{https://www.jstage.jst.go.jp/browse/biophysico/}
   % {\textcolor{black}{https://www.jstage.jst.go.jp/browse/biophysico/}}};
   {https://www.jstage.jst.go.jp/browse/biophysico/};
  \draw [line width=0.2mm] (\@dimB,0) -- (\textwidth,0);
 \end{tikzpicture}%
 \hss}\par
}

\def\@maketitle{%
 \newpage
 %\null
 \@make@BPPBhead
 \nointerlineskip
 \vskip5.3mm
 {\large\bfseries\itshape \@bppbcategory}\par % lineskip 14pt
 \vskip3.9mm
 {\bfseries\fontsize{16\p@}{18\p@}\selectfont % 18pt OK
  \leavevmode\ignorespaces\@title
   \ifx\@subtitle\@empty\else
    \unskip:\ \ignorespaces\@subtitle
   \fi
  \par
 }%
 \vskip6mm
 {\large % lineskip 14pt
  \@outputauthorlist\par
 }%
 \vskip3.3mm
 {\itshape
  \@affiliate\par
 }%
 \vskip4.6mm
 \@received; \@accepted;\par
 \vskip-.2mm
 \@released\par
 \vskip-.2mm
 Edited by \@edited\par
 \vskip8.3mm % baseline 12.5mm
 %% Abstract
}

\newif\if@outputrunningtitle\@outputrunningtitletrue
\def\bppbcategory#1{%
 \def\tmp@cat@Editorial{Editorial}%
 \def\tmp@cat@CP{Commentary and Perspective}%
 \def\tmp@cat{#1}%
 \ifx\tmp@cat\tmp@cat@Editorial
  \@outputrunningtitlefalse
 \else
  \ifx\tmp@cat\tmp@cat@CP
   \@outputrunningtitlefalse
  \fi
 \fi
 \gdef\@bppbcategory{#1}}
\def\@bppbcategory{category here}

\def\title{\@ifnextchar[% ]
 {\d@title}{\s@title}}
\def\d@title[#1]#2{\gdef\@title{#2}%
 \gdef\head@title{#1}%
}
\def\s@title#1{\gdef\@title{#1}%
 \gdef\head@title{\def\\{\unskip\ignorespaces}#1}%
}
\def\@title{}
\def\head@title{}

\def\subtitle#1{\gdef\@subtitle{#1}}
\def\@subtitle{}

\def\received#1#2#3{\def\@temp@m{#2}\ifx\@temp@m\@empty\def\@temp@m{0}\fi
 \def\@recmonth{%
  \ifcase\@temp@m Xxx\or January\or February\or March\or April\or 
   May\or June\or July\or August\or September\or October\or 
   November\or December\fi
 }%
 \xdef\@received{Received\ \@recmonth\ \ignorespaces #3\unskip, 
  \ignorespaces #1\unskip}%
}
\def\@received{Received XX Xxx, \@Year}%

\def\accepted#1#2#3{\def\@temp@m{#2}\ifx\@temp@m\@empty\def\@temp@m{0}\fi
 \def\@recmonth{%
  \ifcase\@temp@m Xxx\or January\or February\or March\or April\or 
   May\or June\or July\or August\or September\or October\or 
   November\or December\fi
 }%
 \xdef\@accepted{Accepted\ \@recmonth\ \ignorespaces #3\unskip, 
  \ignorespaces #1\unskip}%
}
\def\@accepted{Accepted XX Xxx, \@Year}%

\def\released#1#2#3{\def\@temp@m{#2}\ifx\@temp@m\@empty\def\@temp@m{0}\fi
 \def\@pubmonth{%
  \ifcase\@temp@m Xxx\or January\or February\or March\or April\or 
   May\or June\or July\or August\or September\or October\or 
   November\or December\fi
 }%
 \xdef\@released{Released online in J-STAGE as advance publication\ 
  \@pubmonth\ \ignorespaces #3\unskip, 
  \ignorespaces #1\unskip}}
\def\@released{Released online in J-STAGE as advance publication XX Xxx, \@Year}

\def\edited#1{\gdef\@edited{#1}}
\gdef\@edited{Xxx Xxx}

\def\abstract{\bfseries}
\def\endabstract{\par
 \vskip\baselineskip
}
\def\keywords{\par
 \noindent
 {\bfseries Key words}: 
 \ignorespaces
}
\def\endkeywords{%
 \vskip4.3mm
}

\def\significance{%
 \tcbset{enhanced,
         breakable,
         colback=white,
         colframe=blue!75!black, %??
         before skip=\z@,
         after skip=5mm,
         boxrule=0.5mm,
         arc=10\p@,
         boxsep=\z@,
         left=8\p@,
         right=8\p@,
         top=10\p@,
         bottom=8\p@,
         bottomrule at break=\z@,
         toprule at break=\z@,
         pad at break=\z@,
         %%
         title={$\blacktriangleleft$ Significance $\blacktriangleright$},
         colbacktitle=white,
         fonttitle=\bfseries\itshape,
         coltitle=blue!75!black, %??
         attach boxed title to top center={yshift=-4.5\p@},
         center title,
         boxed title style={%
           colframe=white,
           boxsep=\z@,
           boxrule=\z@,
           left=0.6mm,
           right=0.6mm,
           top=\z@,
           bottom=\z@,
         },
        }%
 \begin{tcolorbox}[enlargepage flexible=.5\baselineskip]%
  \ignorespaces
}
\def\endsignificance{\par
 \end{tcolorbox}
}

\setcounter{secnumdepth}{0}
\newcounter {section}
\newcounter {subsection}[section]
\newcounter {subsubsection}[subsection]
%\newcounter {paragraph}[subsubsection]
%\newcounter {subparagraph}[paragraph]
\renewcommand \thesection {\@arabic\c@section}
\renewcommand\thesubsection   {\thesection.\@arabic\c@subsection}
\renewcommand\thesubsubsection{\thesubsection.\@arabic\c@subsubsection}
%\renewcommand\theparagraph    {\thesubsubsection.\@arabic\c@paragraph}
%\renewcommand\thesubparagraph {\theparagraph.\@arabic\c@subparagraph}

\newcommand\section{\@startsection{section}{1}{\z@}% }{
 {1\baselineskip \@plus.1\baselineskip \@minus.1\baselineskip}%
 {1\baselineskip \@plus.1\baselineskip \@minus.1\baselineskip}%
 {\normalfont\normalsize\bfseries}}
\newcommand\subsection{\@startsection{subsection}{2}{\z@}% }{
 {1\baselineskip \@plus.1\baselineskip \@minus.1\baselineskip}%
 {.001\p@ \@plus.05\baselineskip \@minus .001\p@}%
 {\normalfont\normalsize\bfseries}}
\newcommand\subsubsection{\@startsection{subsubsection}{3}{\z@}% }{
 {.5\baselineskip \@plus.1\baselineskip \@minus.1\baselineskip}%
 {.001\p@ \@plus.05\baselineskip \@minus .001\p@}%
 {\normalfont\normalsize\bfseries}}
%\newcommand\paragraph{\@startsection{paragraph}{4}{\z@}%
%                                    {3.25ex \@plus1ex \@minus.2ex}%
%                                    {-1em}%
%                                    {\normalfont\normalsize\bfseries}}
%\newcommand\subparagraph{\@startsection{subparagraph}{5}{\parindent}%
%                                       {3.25ex \@plus1ex \@minus .2ex}%
%                                       {-1em}%
%                                      {\normalfont\normalsize\bfseries}}

\newcommand\appendix{\par
 \setcounter{section}{0}%
 \setcounter{subsection}{0}%
 \gdef\thesection{\@Alph\c@section}%
}

\if@twocolumn
  \setlength\leftmargini  {2em}
\else
  \setlength\leftmargini  {2.5em}
\fi
\leftmargin  \leftmargini
\setlength\leftmarginii  {2.2em}
\setlength\leftmarginiii {1.87em}
\setlength\leftmarginiv  {1.7em}
\if@twocolumn
  \setlength\leftmarginv  {.5em}
  \setlength\leftmarginvi {.5em}
\else
  \setlength\leftmarginv  {1em}
  \setlength\leftmarginvi {1em}
\fi
\setlength  \labelsep  {.5em}
\setlength  \labelwidth{\leftmargini}
\addtolength\labelwidth{-\labelsep}
\@beginparpenalty\z@ % -\@lowpenalty
\@endparpenalty\z@ %   -\@lowpenalty
\@itempenalty\z@ %     -\@lowpenalty

\renewcommand\theenumi{\@arabic\c@enumi}
\renewcommand\theenumii{\@alph\c@enumii}
\renewcommand\theenumiii{\@roman\c@enumiii}
\renewcommand\theenumiv{\@Alph\c@enumiv}
\newcommand\labelenumi{\theenumi.}
\newcommand\labelenumii{(\theenumii)}
\newcommand\labelenumiii{\theenumiii.}
\newcommand\labelenumiv{\theenumiv.}
\renewcommand\p@enumii{\theenumi}
\renewcommand\p@enumiii{\theenumi(\theenumii)}
\renewcommand\p@enumiv{\p@enumiii\theenumiii}

\renewenvironment{enumerate}
  {\ifnum \@enumdepth >3\relax\@toodeep\else
   \advance\@enumdepth\@ne
   \edef\@enumctr{enum\romannumeral\the\@enumdepth}%
   \list{\csname label\@enumctr\endcsname}{% 
   %\expandafter \list \csname label\@enumctr\endcsname{%
     \ifnum \@listdepth=\@ne
      \topsep.5\baselineskip
     \else
      \topsep\z@
     \fi
     \parsep\z@\partopsep\z@\itemsep\z@
     \ifnum\@enumdepth=\thr@@
      \settowidth{\labelwidth}{iii.}%
     \else
      \settowidth{\labelwidth}{\csname label\@enumctr\endcsname}%
     \fi
     \itemindent\z@
     \labelsep5\p@
     \leftmargin\labelwidth
     \advance\leftmargin \labelsep
     \advance\leftmargin 10\p@
     \listparindent10\p@
     \clubpenalty\z@
     \widowpenalty\z@
     \@itempenalty\z@
     \usecounter{\@enumctr}%
     \def\makelabel##1{\hss\llap{##1}}}%
   \fi}{\endlist}

\newcommand{\labelitemi}{\leavevmode\labelitemfont
 \hbox to 10\p@{\hss \textbullet\hss}}
\newcommand{\labelitemii}{\leavevmode\labelitemfont
 \hbox to 10\p@{\hss \textendash\hss}}
\newcommand{\labelitemiii}{\leavevmode\labelitemfont
 \hbox to 10\p@{\hss \textasteriskcentered\hss}}
\newcommand{\labelitemiv}{\leavevmode\labelitemfont
 \hbox to 10\p@{\hss \textperiodcentered\hss}}
\newcommand\labelitemfont{\normalfont}

\renewenvironment{itemize}
  {\ifnum \@itemdepth >3\relax\@toodeep\else
   \advance\@itemdepth\@ne
   \edef\@itemitem{labelitem\romannumeral\the\@itemdepth}%
   \expandafter
   \list{\csname \@itemitem\endcsname}{% 
   %\expandafter \list \csname \@itemitem\endcsname{%
     \ifnum \@listdepth=\@ne
      \topsep.5\baselineskip
     \else
      \topsep\z@
     \fi
     \parsep\z@\partopsep\z@\itemsep\z@
     \labelwidth10\p@
     \labelsep\z@
     \leftmargin10\p@
     \advance\leftmargin 10\p@
     \listparindent10\p@
     \clubpenalty\z@
     \widowpenalty\z@
     \@itempenalty\z@
     \def\makelabel##1{\hss\llap{##1}}}%
   \fi}{\endlist}

\newenvironment{description}
  {\list{}{%
   \ifnum \@listdepth=\@ne
    \topsep.5\baselineskip
   \else
    \topsep\z@
   \fi
   \parsep\z@\partopsep\z@\itemsep\z@
   \labelwidth\z@ \itemindent-\leftmargin
   \let\makelabel\descriptionlabel
  }}
  {\endlist}
\newcommand*\descriptionlabel[1]{\hspace\labelsep
 \normalfont\bfseries #1}

\newenvironment{verse}
               {\let\\\@centercr
                \list{}{\itemsep      \z@
                        \itemindent   -1.5em%
                        \listparindent\itemindent
                        \rightmargin  \leftmargin
                        \advance\leftmargin 1.5em}%
                \item\relax}
               {\endlist}

\newenvironment{quotation}
 {\list{}{%
   \topsep.5\baselineskip\parsep\z@\partopsep\z@\itemsep\z@
   \listparindent 1.5em%
   \itemindent\listparindent
   \rightmargin\leftmargin
   \parsep\z@ \@plus\p@}%
   \item\relax}
 {\endlist}
\newenvironment{quote}
 {\list{}{%
   \topsep.5\baselineskip\parsep\z@\partopsep\z@\itemsep\z@
   \rightmargin\leftmargin}%
   \item\relax}
 {\endlist}

\def\@verbatim{%
  \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
  \trivlist \item\relax
  \if@minipage\else\vskip2\parskip\fi
  \leftskip\@totalleftmargin\rightskip\z@skip
  \parindent\z@\parfillskip\@flushglue\parskip\z@skip
  \@@par
  \language\l@nohyphenation
  \@tempswafalse
  \def\par{%
    \if@tempswa
      \leavevmode \null \@@par\penalty\interlinepenalty
    \else
      \@tempswatrue
      \ifhmode\@@par\penalty\interlinepenalty\fi
    \fi}%
  \let\do\@makeother \dospecials
  \obeylines \verbatim@font \@noligs
  \everypar \expandafter{\the\everypar \unpenalty}%
}

\setlength\arraycolsep{5\p@}
\setlength\tabcolsep{6\p@}
\setlength\arrayrulewidth{.4\p@}
\setlength\doublerulesep{2\p@}
\setlength\tabbingsep{\labelsep}
\skip\@mpfootins = \skip\footins

\setlength\fboxsep{3\p@}
\setlength\fboxrule{.4\p@}

\renewcommand\theequation{\@arabic\c@equation}
\def\eqnarray{%
    \stepcounter{equation}%
    \def\@currentlabel{\p@equation\theequation}%
    \global\@eqnswtrue\m@th
    \global\@eqcnt\z@
    \tabskip\mathindent
    \let\\=\@eqncr
    \setlength\abovedisplayskip{\topsep}%
    \ifvmode
      \addtolength\abovedisplayskip{\partopsep}%
    \fi
    \addtolength\abovedisplayskip{\parskip}%
    \setlength\belowdisplayskip{\abovedisplayskip}%
    \setlength\belowdisplayshortskip{\abovedisplayskip}%
    \setlength\abovedisplayshortskip{\abovedisplayskip}%
    $$\everycr{}\halign to\linewidth% $$
    \bgroup
      \hskip\@centering$\displaystyle\tabskip\z@skip{##}$\@eqnsel
      &\global\@eqcnt\@ne \hfil$\displaystyle{{}##{}}$\hfil
      &\global\@eqcnt\tw@
        $\displaystyle{##}$\hfil \tabskip\@centering
      &\global\@eqcnt\thr@@ \hb@xt@\z@\bgroup\hss##\egroup
    \tabskip\z@skip\cr
    }

\newcounter{figure}
\renewcommand\thefigure{\@arabic\c@figure}
\def\fps@figure{tbp}
\def\ftype@figure{1}
\def\ext@figure{lof}
\def\fnum@figure{\figurename\nobreakspace\thefigure}
\newenvironment{figure}
               {\abovecaptionskip.5\baselineskip\belowcaptionskip\z@
                \let\center\Center\let\endcenter\endCenter\@float{figure}}
               {\end@float}
\newenvironment{figure*}
               {\abovecaptionskip.5\baselineskip\belowcaptionskip\z@
                \let\center\Center\let\endcenter\endCenter\@dblfloat{figure}}
               {\end@dblfloat}
\newcounter{table}
\renewcommand\thetable{\@arabic\c@table}
\def\fps@table{tbp}
\def\ftype@table{2}
\def\ext@table{lot}
\def\fnum@table{\tablename\nobreakspace\thetable}
\newenvironment{table}
               {\abovecaptionskip\z@\belowcaptionskip.25\baselineskip
                \let\center\Center\let\endcenter\endCenter\@float{table}}
               {\end@float}
\newenvironment{table*}
               {\abovecaptionskip\z@\belowcaptionskip.25\baselineskip
                \let\center\Center\let\endcenter\endCenter\@dblfloat{table}}
               {\end@dblfloat}

\newlength\abovecaptionskip
\newlength\belowcaptionskip

\def\Center{\topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
 \trivlist \centering\item\relax}
\def\endCenter{\endtrivlist}

\long\def\@makecaption#1#2{%
  \vskip\abovecaptionskip
  \sbox\@tempboxa{{\bfseries #1}\hskip10\p@ #2}%
  \ifdim \wd\@tempboxa >\hsize
    {\bfseries #1}\hskip10\p@ #2\par
  \else
    \global \@minipagefalse
    \hb@xt@\hsize{\hfil\box\@tempboxa\hfil}%
  \fi
  \vskip\belowcaptionskip}

\DeclareOldFontCommand{\rm}{\normalfont\rmfamily}{\mathrm}
\DeclareOldFontCommand{\sf}{\normalfont\sffamily}{\mathsf}
\DeclareOldFontCommand{\tt}{\normalfont\ttfamily}{\mathtt}
\DeclareOldFontCommand{\bf}{\normalfont\bfseries}{\mathbf}
\DeclareOldFontCommand{\it}{\normalfont\itshape}{\mathit}
\DeclareOldFontCommand{\sl}{\normalfont\slshape}{\@nomath\sl}
\DeclareOldFontCommand{\sc}{\normalfont\scshape}{\@nomath\sc}
\DeclareRobustCommand*\cal{\@fontswitch\relax\mathcal}
\DeclareRobustCommand*\mit{\@fontswitch\relax\mathnormal}

\newdimen\bibindent
\setlength\bibindent{1.5em}
\newenvironment{thebibliography}[1]
     {\section*{\refname}%
      \vskip-.5\baselineskip % OK
      \nopagebreak
      %\@mkboth{\MakeUppercase\refname}{\MakeUppercase\refname}%
      \list{\@biblabel{\@arabic\c@enumiv}}%
           {\settowidth\labelwidth{\@biblabel{#1}}%
            \topsep\z@\parsep\z@\partopsep\z@\itemsep\z@
            \leftmargin\labelwidth
            \advance\leftmargin\labelsep
            \@openbib@code
            \usecounter{enumiv}%
            \let\p@enumiv\@empty
            \renewcommand\theenumiv{\@arabic\c@enumiv}}%
      \sloppy
      \clubpenalty\z@ %4000
      \@clubpenalty \clubpenalty
      \widowpenalty\z@ %4000
      \sfcode`\.\@m}
     {\def\@noitemerr
       {\@latex@warning{Empty `thebibliography' environment}}%
      \endlist}
\newcommand\newblock{\hskip .11em\@plus.33em\@minus.07em}
\let\@openbib@code\@empty

\renewcommand\footnoterule{%
  \kern-3\p@
  \hrule\@width1\columnwidth
  \kern2.6\p@}
\newcommand\@makefntext[1]{%
    \parindent 1em%
    \noindent
    \hb@xt@1.8em{\hss\@makefnmark}#1}

%\newcommand\contentsname{Contents}
%\newcommand\listfigurename{List of Figures}
%\newcommand\listtablename{List of Tables}
\newcommand\refname{References}
%\newcommand\indexname{Index}
\newcommand\figurename{Figure}
\newcommand\tablename{Table}
%\newcommand\partname{Part}
\newcommand\appendixname{Appendix}
%\newcommand\abstractname{Abstract}

\def\today{\ifcase\month\or
  January\or February\or March\or April\or May\or June\or
  July\or August\or September\or October\or November\or December\fi
  \space\number\day, \number\year}

\setlength\columnsep{10\p@}
\setlength\columnseprule{0\p@}

\hbadness4000
%\vbadness10001
\tolerance4000\pretolerance\m@ne
\clubpenalty\z@
\widowpenalty\z@

\AtBeginDocument{%
 \displaywidowpenalty\z@
 \interdisplaylinepenalty\z@
 \predisplaypenalty\z@
 \postdisplaypenalty\z@
 %% hyperref
 \@ifpackageloaded{hyperref}{%
  \let\bppb@href\href
  \def\href#1#2{\bppb@href{#1}{\color{blue}#2}}%
  \Hy@AtBeginDocument{\def\@pdfborderstyle{/S/U/W 1}}%
 }{\def\href#1#2{\url{#2}}}%
 %% url
 \@ifpackageloaded{url}{%
  \DeclareUrlCommand\bppb@email{\urlstyle{rm}}%
 }{\RequirePackage{url}\DeclareUrlCommand\bppb@email{\urlstyle{rm}}}%
 %% \mathindent
 \mathindent3\parindent
 %% amsmath
 \@ifpackageloaded{amsmath}{%
  \@mathmargin3\parindent \@plus\z@ \@minus\parindent
  \multlinegap3\parindent
 }{}%
 %% enumerate.sty
 \@ifpackageloaded{enumerate}{%
  \def\@@enum@[#1]{%
    \@enLab{}\let\@enThe\@enQmark
    \@enloop#1\@enum@
    \ifx\@enThe\@enQmark\@warning{The counter will not be printed.%
     ^^J\space\@spaces\@spaces\@spaces The label is: \the\@enLab}\fi
    \expandafter\edef\csname label\@enumctr\endcsname{\the\@enLab}%
    \expandafter\let\csname the\@enumctr\endcsname\@enThe
    \csname c@\@enumctr\endcsname7
    \expandafter\settowidth
              \csname leftmargin\romannumeral\@enumdepth\endcsname
              {\the\@enLab\hspace{\labelsep}}% 
    \@enum@}%
  \def\@enum@{%
   \list{\csname label\@enumctr\endcsname}%
    {\labelsep5\p@
     \expandafter\leftmargin\csname leftmargin\romannumeral\@enumdepth\endcsname
     \listparindent10\p@
     \itemindent\z@
     \ifnum \@listdepth=\@ne
      \advance \leftmargin 10\p@
      \topsep.5\baselineskip
     \else
      \topsep\z@
     \fi
     \parsep\z@\partopsep\z@\itemsep\z@
     %%
     \usecounter{\@enumctr}\def\makelabel##1{\hss\llap{##1}}}%
  }%
 }{}%
 %%
 \enlargethispage{12mm}% OK
}

\AtEndDocument{%
 \ifnum\c@page=\@ne\else
  \enlargethispage{1\baselineskip}%
 \fi
 \vskip7.5mm %??
 \nopagebreak
%%%% bppb_cc.pdf is ignored.
%%% \IfFileExists{bppb_cc.pdf}{%
%%%  \noindent
%%%  \hbox to \textwidth{\hss
%%%   \includegraphics[clip=true,bb=0 0 482pt 29pt]{bppb_cc.pdf}%
%%%  \hss}%
%%% }{\bppb@warning{bppb_cc.pdf is not found}}%
%%%%
% \clearpage
% \addtocounter{page}{-1}%
% \immediate\write\@auxout
%  {\string\newlabel{bppb@lastpage}{{}{\thepage}}}%
% %\addtocounter{page}{1}%
}

\pagestyle{headings}
\pagenumbering{arabic}
%\if@twoside
%\else
 \sloppy
 \raggedbottom
%\fi
\if@twocolumn
 \twocolumn
 \sloppy
 \flushbottom
\else
 \onecolumn
\fi
\endinput
