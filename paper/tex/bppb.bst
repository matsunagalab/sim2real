ENTRY
   {  address
      author
      booktitle
      chapter
      doi
      edition
      editor
      howpublished
      institution
      journal
      key
      month
      note
      number
      organization
      pages
      publisher
      school
      series
      title
      type
      url
      volume
      year
   }
   {}
   { label }

INTEGERS
   {  output.state
      before.all
      mid.sentence
      after.block
      after.sentence
      after.editors
      omit.period
      last.entry.is.url
      nextpos
      tempnum
   }

STRINGS { s t tempstr thesis.type }

FUNCTION {not}
{     {  #0  }
      {  #1  }
   if$
}

FUNCTION {and}
{     'skip$
      {  pop$ #0  }
   if$
}

FUNCTION {or}
{     {  pop$ #1  }
      'skip$
   if$
}

INTEGERS{  numentries  }

FUNCTION {init.numentries}
{  #0 'numentries :=  }

FUNCTION {count.entries}
{  #1 numentries + 'numentries :=  }

FUNCTION {format.numentries}
{  "" 't :=
   numentries int.to.str$ 's :=
      {  s empty$ not  }
      {  s #2 global.max$ substring$ 's :=
         t "9" * 't :=
      }
   while$
   t
}

FUNCTION {begin.bib}
{  preamble$ empty$
      'skip$
      {  preamble$ write$ newline$  }
   if$
   "\begin{thebibliography}{"  format.numentries  * "}" * write$ newline$
}

FUNCTION {end.bib}
{  newline$
   "\end{thebibliography}" write$ newline$
}

FUNCTION {init.state.consts}
{  #0 'before.all :=
   #1 'mid.sentence :=
   #2 'after.sentence :=
   #0 'after.editors :=
   #0 'omit.period :=
   #0 'last.entry.is.url :=
}


FUNCTION {endline}
{  duplicate$ empty$
      'skip$
      {   before.all output.state =
             'skip$
             {  after.sentence 'output.state :=  }
          if$
      }
   if$
}


FUNCTION {output.nonnull.common}
{  't :=
   's :=
   output.state mid.sentence =
      {  t * write$  }
      {  output.state after.sentence =
            {  omit.period
                  {  #0 'omit.period :=  }
                  'add.period$
               if$
               write$
               newline$
            }
            'write$
         if$
         mid.sentence 'output.state :=
      }
   if$
   s
}

FUNCTION {output.nonnull}
{  ", " output.nonnull.common
}

FUNCTION {output.nonnull.nocomma}
{  " " output.nonnull.common
}


FUNCTION {output}
{  duplicate$ empty$
      'pop$
      'output.nonnull
   if$
}

FUNCTION {output.title}
{  duplicate$ empty$
      'pop$
      'output.nonnull.nocomma
   if$
}

FUNCTION {output.title.check}
{  duplicate$ empty$
      {  "empty title in " * cite$ * warning$  }
      'output.nonnull.nocomma
   if$
}

FUNCTION {output.check}
{  't :=
   duplicate$ empty$
      {  pop$
         "empty " t * " in " * cite$ * warning$
      }
      'output.nonnull
   if$
}

FUNCTION {output.check.nocomma}
{  't :=
   duplicate$ empty$
      {  pop$
         "empty " t * " in " * cite$ * warning$
      }
      'output.nonnull.nocomma
   if$
}

FUNCTION {output.bibitem}
{  newline$
   "\bibitem{" write$
   cite$ write$
   "}" write$
   newline$
   ""
   before.all 'output.state :=
   #0 'omit.period :=
   #0 'last.entry.is.url :=
}

FUNCTION {fin.entry}
{  last.entry.is.url
      {  #0 'last.entry.is.url := }
      'add.period$
   if$
   write$
   newline$
}

FUNCTION {new.sentence}
{  output.state before.all =
      'skip$
      {  after.sentence 'output.state :=  }
   if$
}

FUNCTION {new.sentence.check}
{  empty$
      'skip$
      'new.sentence
   if$
}

FUNCTION {field.or.null}
{  duplicate$ empty$
      {  pop$ ""  }
      'skip$
   if$
}

FUNCTION {emphasize}
{  duplicate$ empty$
     {  pop$ ""  }
     {  "\textbf{" swap$ * "}" *   }
   if$
}

INTEGERS { namepos namesleft numnames }

FUNCTION {format.names}
{  's :=
   #1 'namepos :=
   s num.names$ 'numnames :=
   numnames 'namesleft :=
      {  namesleft #0 >  }
      {  s namepos "{vv~}{ll}{, f.}{, jj}" format.name$ 't :=
         namepos #6 >
            {  ", et~al." *
               #0 'namesleft :=
            }
            {  namepos #1 >
                  {  namesleft #1 >
                        {  ", " * t *  }
                        {   numnames #2 >
                              { "," * }
                              'skip$
                           if$
                           t "others" =
                              {  " et~al." *  }
                              {  " " * t *  }
                           if$
                        }
                     if$
                  }
                  't
               if$
            }
         if$
         namepos #1 + 'namepos :=
         namesleft #1 - 'namesleft :=
      }
   while$
}


FUNCTION {format.authors}
{  author empty$
      {  ""  }
      {  author format.names  }
   if$
}

FUNCTION {format.editors}
{  editor empty$
      {  ""  }
      {  "("
         editor format.names *
         editor num.names$ #1 >
            {  " eds." *  }
            {  " ed." *  }
         if$
         ")" *
      }
   if$
}

FUNCTION {format.title}
{  title field.or.null  }

FUNCTION {n.dashify}
{  't :=
   ""
      {  t empty$ not  }
      {  t #1 #1 substring$ "-" =
            {  t #1 #2 substring$ "--" = not
                  {  "--" *
                     t #2 global.max$ substring$ 't :=
                  }
                  {   { t #1 #1 substring$ "-" = }
                      { "-" *
                        t #2 global.max$ substring$ 't :=
                      }
                    while$
                  }
               if$
            }
            {  t #1 #1 substring$ *
               t #2 global.max$ substring$ 't :=
            }
         if$
      }
   while$
}

FUNCTION {format.date}
{  year empty$
      {  month empty$
            {  ""  }
            {  "there's a month but no year in " cite$ * warning$
               ""
            }
         if$
      }
      {  year }
   if$
   duplicate$ empty$
      'skip$
      {  "(" swap$ * ")" *  }
   if$
}

FUNCTION {format.book.date}
{  publisher empty$
      {  ""  }
      {  address empty$
            {  publisher  }
            {  publisher ", " * address *  }
         if$
      }
   if$
   's :=
   year empty$
      {  month empty$
            {  ""  }
            {  "there's a month but no year in " cite$ * warning$
               ""
            }
         if$
      }
      {  year }
   if$
   't :=
   s empty$
      {  t empty$
            {  ""  }
            {  "(" t * ")" * }
         if$
      }
      {  t empty$
            {  "(" s * ")" * }
            {  "(" s * ", " * t * ")" * }
         if$
      }
   if$
}

FUNCTION {tie.or.space.connect}
{  duplicate$ text.length$ #3 <
      {  "~"  }
      {  " "  }
   if$
   swap$ * *
}

FUNCTION {either.or.check}
{  empty$
      'pop$
      {  "can't use both " swap$ * " fields in " * cite$ * warning$  }
   if$
}

FUNCTION {format.book.volume}
{  volume empty$
      {  ""  }
      {  "vol." volume tie.or.space.connect
         series empty$
            'skip$
            {  " of " * series *  }
         if$
         "volume and number" number either.or.check
      }
   if$
}

FUNCTION {format.number.series}
{  volume empty$
      {  number empty$
            {  series field.or.null  }
            {  output.state mid.sentence =
                  {  "number"  }
                  {  after.editors
                        {  "number"
                           #0 'after.editors :=
                        }
                        {  "Number"  }
                     if$
                    
                  }
               if$
               number tie.or.space.connect
               series empty$
                  {  "there's a number but no series in " cite$ * warning$  }
                  {  " in " * series *  }
               if$
            }
         if$
      }
      {  ""  }
   if$
}

FUNCTION {format.edition}
{  edition empty$
      {  ""  }
      {  output.state mid.sentence =
            {  edition "l" change.case$ " edition" *  }
            {  edition "t" change.case$ " edition" *  }
         if$
      }
   if$
}

INTEGERS { multiresult }

FUNCTION {multi.page.check}
{  't :=
   #0 'multiresult :=
      {  multiresult not
         t empty$ not
         and
      }
      {  t #1 #1 substring$
         duplicate$ "-" =
         swap$ duplicate$ "," =
         swap$ "+" =
         or or
            {  #1 'multiresult :=  }
            {  t #2 global.max$ substring$ 't :=  }
         if$
      }
   while$
   multiresult
}

FUNCTION {format.pages}
{   pages empty$
       {  ""  }
       {  pages n.dashify  }
   if$
}

FUNCTION {format.book.pages}
{   pages empty$
       {  "" } 
       {  pages multi.page.check
             {  "pp." pages n.dashify tie.or.space.connect  }
             {  "p." pages tie.or.space.connect  }
          if$
       }
   if$
}

FUNCTION {format.vol.num.pages}
{  volume field.or.null
   number empty$
      'skip$
      {  %%% "(" number * ")" * *
         volume empty$
            {  "there's a number but no volume in " cite$ * warning$  }
            'skip$
         if$
      }
   if$
   pages empty$
      'skip$
      {  duplicate$ empty$
            {  pop$ format.pages  }
            {  ", " * format.pages *  }
         if$
      }
   if$
}

FUNCTION {format.vol.pages}
{  volume field.or.null
   pages empty$
      'skip$
      {  duplicate$ empty$
            {  pop$ format.pages  }
            {  ", " * format.pages *  }
         if$
      }
   if$
}

FUNCTION {format.chapter.pages}
{  chapter empty$
      'format.book.pages
      {  type empty$
            {  "chapter"  }
            {  type "l" change.case$  }
         if$
         chapter tie.or.space.connect
         pages empty$
           'skip$
           {  ", " * format.book.pages *  }
         if$
      }
   if$
}

FUNCTION {format.in.ed.booktitle}
{  booktitle empty$
      {  ""  }
      {  editor empty$
           {  "in " booktitle *  }
           {  "in " booktitle *
              output.nonnull.nocomma
              endline
              format.editors
           }
         if$
      }
   if$
}

FUNCTION {empty.misc.check}
{  author empty$ title empty$ howpublished empty$
   month empty$ year empty$ note empty$
   and and and and and
   key empty$ not and
     {  "all relevant fields are empty in " cite$ * warning$  }
     'skip$
   if$
}

FUNCTION {format.thesis.type}
{  type empty$
      'skip$
      {  pop$
         type "t" change.case$
      }
   if$
}

FUNCTION {format.tr.number}
{  type empty$
      {  "Technical Report"  }
      'type
   if$
   number empty$
     {  "t" change.case$  }
     {  number tie.or.space.connect  }
   if$
}

FUNCTION {reduce.spaces}
{  'tempstr :=
   "" ""
      {  tempstr empty$ not }
      {  tempstr #1 #1 substring$ " " =
            {  swap$ duplicate$ empty$
                  {  swap$ }
                  {  swap$ " " * }
               if$
            }
            {  tempstr #1 #1 substring$ * * "" }
         if$
         tempstr #2 global.max$ substring$ 'tempstr :=
      }
   while$
   pop$
}

FUNCTION {deescape.url}
{  's :=
   ""
      {  s empty$ not }
      {  #2 'nextpos :=
         s #1 #1 substring$ 't :=
         t "\" =
            {  s #2 #1 substring$ 't :=
               t empty$
                  'skip$
                  {  s #2 #13 substring$ "textbackslash" =
                        {  "\" *
                           #15 'nextpos :=
                              {  s nextpos #1 substring$ " " = }
                              {  nextpos #1 + 'nextpos := }
                           while$
                        }
                        {  s #2 #14 substring$ "textunderscore" =
                              {  "_" *
                                 #16 'nextpos :=
                                    {  s nextpos #1 substring$ " " = }
                                    {  nextpos #1 + 'nextpos := }
                                 while$
                              }
                              {  t "~" =  t "^" =  or
                                    {  t *
                                       s #3 #2 substring$ "{}" =
                                          {  #5 'nextpos := }
                                          {  #3 'nextpos := }
                                       if$
                                    }
                                    {  t *
                                       #3 'nextpos :=
                                    }
                                 if$
                              }
                           if$
                        }
                     if$
                  }
               if$
            }
            {  t "{" =
                  {  s #2 #1 substring$ "\" =
                        {  s #3 #1 substring$ 't :=
                           t "~" =  t "^" =  or
                              {  t *
                                 s #4 #2 substring$ "{}" =
                                    {  #6 'nextpos := }
                                    {  #4 'nextpos := }
                                 if$
                              }
                              {  t *
                                 #4 'nextpos :=
                              }
                           if$
                        }
                        'skip$
                     if$
                  }
                  {  t "}" =
                        'skip$
                        {  t "$" =
                              {  ""
                                    {  s nextpos #1 substring$ "$" = not }
                                    {  s nextpos #1 substring$ 't :=
                                       t "\" =
                                          {  s nextpos #1 + #1 substring$ "$" =
                                                {  "\$" *
                                                   nextpos #1 + 'nextpos :=
                                                }
                                                {  t * }
                                             if$
                                          }
                                          {  t * }
                                       if$
                                       nextpos #1 + 'nextpos :=
                                    }
                                 while$
                                 reduce.spaces 't :=
                                 t #1 #1 substring$ 'tempstr :=
                                 tempstr "{" =
                                    {  #0 'tempnum :=
                                       t 'tempstr :=
                                          {  tempstr empty$ not }
                                          {  tempnum #1 + 'tempnum :=
                                             tempstr #2 global.max$ substring$ 'tempstr := }
                                       while$
                                       t tempnum #1 substring$ "}" =
                                          {  t #2 tempnum #2 - substring$
                                             reduce.spaces 't :=
                                          }
                                          'skip$
                                       if$
                                    }
                                    'skip$
                                 if$
                                 t #1 #1 substring$ 'tempstr :=
                                 tempstr "\" =
                                    {  t #2 #1 substring$ 'tempstr :=
                                       tempstr "#" =  tempstr "$" =  tempstr "%" =
                                       tempstr "&" =  tempstr "^" =  tempstr "{" =
                                       tempstr "}" =  tempstr "_" =
                                       tempstr #34 int.to.chr$ =
                                       tempstr "`" =  tempstr "'" =
                                       or or or or or or or or or or
                                          {  tempstr * }
                                          {  t #2 #3 substring$ 'tempstr :=
                                             tempstr "sim" =
                                                {  "~" * }
                                                {  tempstr "hat" =
                                                      {  "^" * }
                                                      {  t #2 #5 substring$ 'tempstr :=
                                                         tempstr "tilde" =
                                                            {  "~" * }
                                                            {  t * }
                                                         if$
                                                      }
                                                   if$
                                                }
                                             if$
                                          }
                                       if$
                                    }
                                    {  t * }
                                 if$
                                 nextpos #1 + 'nextpos :=
                              }
                              {  t * }
                           if$
                        }
                     if$
                  }
               if$
            }
         if$
         s nextpos global.max$ substring$ 's :=
      }
   while$
}


FUNCTION {make.url.link}
{  duplicate$ empty$
      'skip$
      {  duplicate$
         deescape.url
         "\href{" swap$ * "}{" * swap$ "}" * *
      }
   if$
}

FUNCTION {format.url.or.doi}
{  #1 'last.entry.is.url :=
   url empty$
      {  doi empty$
            {  #0 'last.entry.is.url :=
               ""
            }
            {  "https://doi.org/" doi *  }
         if$
      }
      {  url  }
   if$
   make.url.link
}



FUNCTION {format.article.crossref}
{  key empty$
     {  journal empty$
           {  "need key or journal for " cite$ * " to crossref " * crossref *
              warning$
              ""
           }
           {  "In " journal *  }
        if$
     }
     {  "In " key *  }
   if$
   " \cite{" * crossref * "}" *
}

FUNCTION {format.crossref.editor}
{  editor #1 "{vv~}{ll}" format.name$
   editor num.names$ duplicate$
   #2 >
      {  pop$ " et~al." *  }
      { #2 <
           'skip$
           {  editor #2 "{ff }{vv }{ll}{ jj}" format.name$ "others" =
                 {   " et~al." *  }
                 {  " and " * editor #2 "{vv~}{ll}" format.name$ *  }
              if$
           }
         if$
      }
   if$
}

FUNCTION {format.book.crossref}
{  volume empty$
      {  "empty volume in " cite$ * "'s crossref of " * crossref * warning$
         "In "
      }
      {  "Volume" volume tie.or.space.connect
         " of " *
      }
   if$
   editor empty$
   editor field.or.null author field.or.null =
   or
      {  key empty$
            {  series empty$
                  {  "need editor, key, or series for " cite$ * " to crossref " *
                     crossref * warning$
                     "" *
                  }
                  {  series *  }
               if$
            }
            {  key *  }
         if$
      }
      {  format.crossref.editor *  }
   if$
   " \cite{" * crossref * "}" *
}

FUNCTION {format.incoll.inproc.crossref}
{  editor empty$
   editor field.or.null author field.or.null =
   or
      {  key empty$
            {  booktitle empty$
                 {  "need editor, key, or booktitle for " cite$ * " to crossref " *
                    crossref * warning$
                    ""
                 }
                 { "In " booktitle * }
               if$
            }
            {  "In " key *  }
         if$
      }
      {  "In " format.crossref.editor *  }
   if$
   " \cite{" * crossref * "}" *
}

FUNCTION {article}
{  output.bibitem
   format.authors "author" output.check
   endline
   format.title output.title.check
   endline
   crossref missing$
      {  journal field.or.null "journal" output.check
         endline
         #1 'omit.period :=
         format.vol.num.pages output
         format.date "year" output.check.nocomma
      }
      {  format.article.crossref output.nonnull
         format.pages output
      }
   if$
   endline
   note output
   endline
   format.url.or.doi output.nonnull
   fin.entry
}

FUNCTION {book}
{  output.bibitem
   author empty$
      {  format.editors "author and editor" output.check  }
      {  format.authors output.nonnull
         crossref missing$
            {  "author and editor" editor either.or.check  }
            'skip$
         if$
      }
   if$
   endline
   format.title "title" output.check
   endline
   crossref missing$
      {  format.book.volume output
         format.number.series output
      }
      {  format.book.crossref output.nonnull  }
   if$
   format.edition output
   #1 'omit.period :=
   endline
   format.book.date "year and publisher" output.check
   endline
   note output
   fin.entry
}

FUNCTION {booklet}
{  output.bibitem
   format.authors output
   endline
   format.title "title" output.check
   endline
   howpublished field.or.null output.nonnull
   #1 'omit.period :=
   endline
   format.book.date output
   endline
   note output
   fin.entry
}

FUNCTION {inbook}
{  output.bibitem
   author empty$
      {  format.editors "author and editor" output.check  }
      {  format.authors output.nonnull
         crossref missing$
            {  "author and editor" editor either.or.check  }
            'skip$
         if$
      }
   if$
   endline
   format.title "title" output.check
   endline
   crossref missing$
      {  format.book.volume output
         format.chapter.pages "chapter and pages" output.check
         format.number.series output
         format.edition output
         #1 'omit.period :=
         endline
         format.book.date "year and publisher" output.check
      }
      {  format.chapter.pages "chapter and pages" output.check
         format.book.crossref output.nonnull
      }
   if$
   endline
   note output
   fin.entry
}

FUNCTION {incollection}
{  output.bibitem
   format.authors "author" output.check
   endline
   format.title "title" output.check
   endline
   crossref missing$
      {  format.in.ed.booktitle "booktitle" output.check
         #1 'after.editors :=
         duplicate$ empty$
            'skip$
            {  write$ newline$
               ""
               before.all 'output.state :=
            }
         if$
         format.book.volume output
         format.number.series output
         format.chapter.pages output
         format.edition output
         #1 'omit.period :=
         endline
         format.book.date "year and pulisher" output.check
      }
      {  format.incoll.inproc.crossref output.nonnull
         format.chapter.pages output
      }
   if$
   endline
   note output
   fin.entry
}

FUNCTION {inproceedings}
{  output.bibitem
   format.authors "author" output.check
   endline
   format.title "title" output.check
   endline
   crossref missing$
      {  format.in.ed.booktitle "booktitle" output.check
         #1 'after.editors :=
         duplicate$ empty$
            'skip$
            {  write$ newline$
               ""
               before.all 'output.state :=
            }
         if$
         format.book.volume output
         format.number.series output
         format.pages output
         address empty$
            {   organization "organization" output.check
                #1 'omit.period :=
                endline
                format.book.date "year and publisher" output.check
            }
            {   address output.nonnull
                #1 'omit.period :=
                endline
                format.date "year" output.check
                endline
                organization output
                publisher output
            }
         if$
      }
      {  format.incoll.inproc.crossref output.nonnull
         format.pages output
      }
   if$
   endline
   note output
   fin.entry
}

FUNCTION {conference} { inproceedings }

FUNCTION {manual}
{  output.bibitem
   author empty$
      {   organization empty$
             'skip$
             {  organization output.nonnull
                address output
             }
         if$
      }
      {  format.authors output.nonnull  }
   if$
   endline
   format.title "title" output.check
   endline
   author empty$
      {  organization empty$
            {  address "address" output.check  }
            'skip$
         if$
      }
      {  organization output.nonnull
         address output.nonnull
      }
   if$
   format.edition output
   #1 'omit.period :=
   endline
   format.date output
   endline
   note output
   fin.entry
}

FUNCTION {thesis.common}
{  'thesis.type :=
   output.bibitem
   format.authors "author" output.check
   endline
   format.title "title" output.check
   endline
   thesis.type format.thesis.type output.nonnull
   school "school" output.check
   address output
   #1 'omit.period :=
   endline
   format.date "year" output.check
   endline
   note output
   fin.entry
}

FUNCTION {mastersthesis}
{  "Master's thesis" thesis.common  }

FUNCTION {phdthesis}
{  "PhD thesis" thesis.common  }

FUNCTION {misc}
{  output.bibitem
   format.authors output
   format.title "title" output.check
   howpublished field.or.null output.nonnull
   #1 'omit.period :=
   endline
   format.date output
   endline
   note output
   fin.entry
   empty.misc.check
}


FUNCTION {proceedings}
{  output.bibitem
   editor empty$
      {  organization output  }
      {  format.editors output.nonnull
         #1 'omit.period :=
      }
   if$
   endline
   format.title "title" output.check
   format.book.volume output
   format.number.series output
   address empty$
      {  editor empty$
           {  publisher "publisher" output.check }
           {  organization "organization" output.check  }
         if$
         publisher output
         #1 'omit.period :=
         endline
         format.date "year" output.check
      }
      {  address output.nonnull
         #1 'omit.period :=
         endline
         format.date "year" output.check
         endline
         editor empty$
            'skip$
            {  organization output  }
         if$
         publisher output
      }
   if$
   endline
   note output
   fin.entry
}

FUNCTION {techreport}
{  output.bibitem
   format.authors "author" output.check
   endline
   format.title "title" output.check
   endline
   format.tr.number output.nonnull
   institution "institution" output.check
   address output
   #1 'omit.period :=
   endline
   format.date "year" output.check
   endline
   note output
   fin.entry
}

FUNCTION {unpublished}
{  output.bibitem
   format.authors "author" output.check
   endline
   format.title "title" output.check
   endline
   note "note" output.check
   #1 'omit.period :=
   endline
   format.date output
   fin.entry
   "Reference `" cite$ * "' is unpublished material (not allowed in reference list)." *
   warning$
}

FUNCTION {default.type} {  misc  }

MACRO {jan} {"January"}

MACRO {feb} {"February"}

MACRO {mar} {"March"}

MACRO {apr} {"April"}

MACRO {may} {"May"}

MACRO {jun} {"June"}

MACRO {jul} {"July"}

MACRO {aug} {"August"}

MACRO {sep} {"September"}

MACRO {oct} {"October"}

MACRO {nov} {"November"}

MACRO {dec} {"December"}

READ

EXECUTE {init.numentries}

ITERATE {count.entries}

EXECUTE {begin.bib}

EXECUTE {init.state.consts}

ITERATE {call.type$}

EXECUTE {end.bib}

