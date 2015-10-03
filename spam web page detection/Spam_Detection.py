import math, collections
import logging
import os, glob
import threading
import urllib2
import time, Queue
import string,socket
import httplib
import re
import itertools
import numpy
import nltk
from collections import defaultdict
from gensim import corpora, models, similarities
from topia.termextract import tag
from stemming.lovins import stem
from nltk.stem.wordnet import WordNetLemmatizer
from httplib import BadStatusLine
from bs4 import BeautifulSoup
from urlparse import urlparse
import re
from collections import Counter

start = time.time()
hosts = []
url_title_map = {}
url_anchor_map = {}
sorted_url_title_map = {}
sorted_url_anchor_map = {}
queue = Queue.Queue()
stoplist = []
urls = []
titlelist = []
finalcategory = ''

fp = open( 'result.txt','w' )

timeout = 15    # variable to store the time to wait for fetching requested page
socket.setdefaulttimeout( timeout )
lmtzr = WordNetLemmatizer()
    
def initialize():
    del hosts[:]
    url_title_map.clear()
    url_anchor_map.clear()
    sorted_url_title_map.clear()
    sorted_url_anchor_map.clear()
    del urls[:]
    del titlelist[:]
    with queue.mutex:
        queue.queue.clear()

#--------------------------------------------------------------
## Fetching HTML code from URL to get TITLE of next Page
#--------------------------------------------------------------
class ThreadUrl(threading.Thread):
    """Threaded Url Grab"""

    globvar = 0
    def __init__( self, queue ):
        threading.Thread.__init__( self )
        self.queue = queue

    def run( self ):
        while True:
            #grabs host from queue
            host = self.queue.get()
            try:
                #grabs urls of hosts and print first 1024 bytes of page
                req = urllib2.Request( host )
                url = urllib2.urlopen( req )
                data = url.read()        
                ThreadUrl.globvar = ThreadUrl.globvar + 1
                title = re.search( '<title>(.*)</title>', data, re.IGNORECASE )

                if title:
                    titlelist.append( title.group(1) )
                    url_title_map[ host ] = title.group( 1 )
                else:
                    titlelist.append( "" )
                    url_title_map[ host ] = ""

                #signals to queue job is done
                self.queue.task_done()            
                
            except urllib2.URLError:                
                url_title_map[ host ] = "" 
                self.queue.task_done()
           
            except socket.timeout:                
                url_title_map[ host ] = ""
                self.queue.task_done()            
                
            except BadStatusLine:
                url_title_map[host] = ""
                self.queue.task_done()

            except urllib2.HTTPError:
                url_title_map[host] = ""
                self.queue.task_done()

            except httplib.HTTPException:
                self.queue.task_done()

            except ( ValueError,urllib2.URLError ) as e:
                url_title_map[ host ] = ""
                self.queue.task_done()

            except socket.gaierror:
                url_title_map[ host ] = ""
                self.queue.task_done()

            except socket.gaierror:
                self.queue.task_done()

            except Exception as e :
                #print e
                url_title_map[ host ] = ""
                self.queue.task_done()

#end of multithread title fetch

#--------------------------------------------------------------
## FETCH TILE FROM URL METHOD TO CALL MUTLITHREADING METHOD
#--------------------------------------------------------------            
def fetch_title_from_urls( hosts ):
    print 'Total number of url\'s to be fetched',len( hosts )

    #spawn a pool of threads, and pass them queue instance
    for i in range(5):
        t = ThreadUrl( queue )
        t.setDaemon( True )
        t.start()

    #populate queue with data
    for host in hosts:
        queue.put( host )

    #wait on the queue until everything has been processed
    queue.join()

    j=0        
    for key in sorted( url_title_map.iterkeys() ):
        for c in string.punctuation:
            url_title_map[ key ] = url_title_map[ key ].replace( c, '' )

        ulist = []
        l=url_title_map[ key ].split()
        [ ulist.append( x ) for x in l if x not in ulist ]
        sorted_url_title_map[ key ] = ' '.join( ulist )

#--------------------------------------------------------------
## Calculate Divergence between (Anchor Text + URL ) and TITLE of next page
#--------------------------------------------------------------
def KLD( parenthtml ):

    atags = []
    taglist = []    
            
    # Do pre-processing on Raw web page
    parenthtml = parenthtml.lower()
    parenthtml = re.sub( "\n"," ", parenthtml )
    parenthtml = re.sub( '<!--.*?-->','', parenthtml )
    atags = re.findall ( '<a.*?</a>', parenthtml )
    # atags stores all the anchor text present on the page

    for i in atags:
        i = re.sub( '<a.*?href','<a href', i )  # do some reprocessing to remove unneccesary stuff in atags
        taglist.append( i )

    cnturl = 0
    cntanchor = 0
    for a in taglist:
        r = re.compile('href="(.*?)"')
        m = r.search(a)
        # Fetch the URL from the anchor text    
        cnturl = cnturl + 1
        if m:
            url = m.group( 1 )
        else:
            url = "-------------------"

        a = re.sub( '<a href.*?>','<a>',a )
        a = re.sub( ' +',' ',a )
        r = re.compile( '<a>(.*?)</a>' )
        m = r.search( a )
        cntanchor = cntanchor+1

        # Fetch the anchor text from atags
        if m:
            anchor = m.group(1)
            anchor = re.sub( "<.*?>", "", anchor )
            anchor = re.sub( "\t", "", anchor )
        else:
            anchor = "++++++++++++"

        # Extracting KEYWORDS from URL
        parse_object = urlparse( url )
        str = parse_object.netloc
        tok = str.split( '.' )

        if( tok[0].lower() == 'www' ):
            tok[0] = tok[ 1 ]            

        path = parse_object.path
        path = path.rsplit('.')[ 0 ]
        path = re.sub( '/',' ',path )
        text1 = tok[ 0 ] + path
        a = anchor + ' ' + text1    # form a string of combination of Anchor text and URL keywords

        # Removing DUPLICATES from URL + ANCHOR Text        
        ulist = []
        l = a.split()
        [ ulist.append( x ) for x in l if x not in ulist ]
        url_anchor_map[ url ] = ' '.join( ulist )

    for c in url_anchor_map:
        hosts.append( c )       # hosts a global var stores all the URL's pointed by the current page

    # Call Threads RUNNER FUNCTION to fetch title of pointed pages
    fetch_title_from_urls( hosts )    
    for key in sorted( url_anchor_map.iterkeys() ):
        sorted_url_anchor_map[key] = url_anchor_map[ key ]
    
    ds = [ sorted_url_title_map,sorted_url_anchor_map ]    
    d = {}
    
    for k in sorted_url_title_map.iterkeys():
        d[ k ] = tuple( d[ k ] for d in ds )

    total_divergence = 0.0
    count = 0
    
    for k in d:
        val1 = ( d[ k ] )[ 0 ]
        val2 = ( d[ k ] )[ 1]
        if( val1 is '' ):
            continue
        
        # val1 IS TITLE OF NEXT PAGE    ......  val2 IS Anchor text + URL combination
        for c in string.punctuation:
            val1 = val1.replace( c, ' ' )
            val2 = val2.replace( c, ' ' )
            
        val1 = ( ' '.join( val1.split() ) ).lower()
        val2 = ( ' '.join( val2.split() ) ).lower()        
        matching=0
        if( len( val1 ) < 167 ):    # in case length of title is < 16 chars then only consider for checking similarity. 
                                    # The length of 167 chars of title was found trough experiment.
            for wordanchor in val2.split():                                                 
                for wordtitle in val1.split():
                    # count the number of similar words b/w two strings
                    if( ( wordanchor in wordtitle or wordtitle in wordanchor ) and wordanchor != ' ' and wordtitle != ' ' ):
                        matching += 1

        if( ( matching/( len( val1.split( ' ' ) )*1.0 ) ) > 1.0 ):
            divergence = 0.0
        else:    
            divergence = 1 - ( matching/( len( val1.split( ' ' ) )*1.0 ) )

        total_divergence += abs( divergence )
        count = count + 1
        
    avg_divergence = 0.0

    try:
        avg_divergence = total_divergence/count
    except ZeroDivisionError:
        print ' div error'
        
    print "modified KLD Divergence %s" % ( avg_divergence )
    fp.write( '\n'+'modified KLD divergence----->' )
    fp.write( '%.7g' % avg_divergence ) 
    
    # In case divergence b/w Title and ( Anchor text+ URL ) > 0.6 then classify as Spam. This 0.6 value is found through experiment on training set.
    if( avg_divergence > 0.6 ):
        return 1
    else:
        return 0

#--------------------------------------------------------------
##  POS RATIO TEST
#--------------------------------------------------------------
def POS_ratio(parenthtml):
    
    tagger = tag.Tagger()
    tagger.initialize()
    
    totalwords = 0
    nounsingular = 0
    nounplural = 0
    propernounsingular = 0
    propernounplural = 0
    adverb = 0
    verb = 0
    pronoun = 0
    adjectives = 0
    conjunction = 0
    determiner = 0
    preposition = 0
    divergence = 0.0
      
    # Do some preprocessing on Raw Web Page        
    parenthtml = parenthtml.lower()
    parenthtml = ' '.join( parenthtml.split() )
    parenthtml = re.sub( "|","",parenthtml )
    parenthtml = re.sub( "&.*?;", "", parenthtml )
    parenthtml = re.sub( "<a.*?</a>", "",parenthtml )
    parenthtml = re.sub( "<script.*?</script>", "",parenthtml )
    parenthtml = re.sub( "<.*?>", "",parenthtml )
    parenthtml = re.sub( "href=\".*\"", "",parenthtml ) 
    a = []
        
    for c in string.punctuation:
        parenthtml = parenthtml.replace( c, '' )

    #Remove Numbers
    for s in parenthtml:
        if s.isdigit():
            parenthtml = parenthtml.replace( s, '' )

    a = re.sub( "[^\w]", " ",parenthtml ).split()
    parenthtml = re.sub( "[^\w]", " ",parenthtml )
 
    # Tag each word in the web page its Part of speech
    tagged = nltk.pos_tag( parenthtml.split() ) 
    counts = Counter( tag for word,tag in tagged )

    for word,count in counts.items():
        totalwords += count

        if( word == 'NN' ):
            nounsingular += count
        if( word == 'NNS' ):
            nounplural += count
        if( word == 'NNP' ):
            propernounsingular += count
        if( word == 'NNPS' ):
            propernounplural += count
        if( word == 'RB' or word == 'RBR' or word == 'RBS' ):
            adverb += count
        if( word == 'JJ' or word == 'JJR' or word == 'JJS' ):
            adjectives += count
        if( word == 'WP' or word == 'PRP' or word == 'PRP$' ):
            pronoun += count
        if( word == 'VB' or word == 'VBD' or word == 'VBG' or word == 'VBN' or word == 'VBP' or word == 'VBZ' ):
            verb += count
        if( word == 'CC' ):
            conjunction += count
        if( word == 'DT' ):
            determiner += count
        if( word == 'IN' ):
            preposition += count
            
    try:
        # Calculate the total divergence by subtracting the actual occurence % of each POS from the Standard occurence percenctage values.
        divergence = ( abs(( nounsingular*100.0/totalwords*1.0 ) - 19.0 )\
                        +abs( ( adverb*100.0/totalwords*1.0 ) - 7.0 )\
                        +abs( ( verb*100.0/totalwords*1.0 )-15.0 )\
                        +abs( ( pronoun*100.0/totalwords*1.0 ) - 9.0 )\
                        +abs( ( adjectives*100.0/totalwords*1.0 )-6.0 )\
                        +abs( ( conjunction*100.0/totalwords*1.0 )-4.0 )\
                        +abs( ( determiner*100.0/totalwords*1.0 )-10.0 )\
                        +abs( ( preposition*100.0/totalwords*1.0 )-13.0 ) )

    except ZeroDivisionError:
        print ' div error'

    print "POS_Ratio Divergence", divergence/100.0
    fp.write( '\n'+'POS_RATIO divergence----->' )
    d = divergence/100.0
    fp.write( '%.7g' % d )  
    
    # In case POS ratio divergence > 0.4 then classify as Spam. This threshold value = 0.4 is found through experiment on training set.
    if( divergence/100.0 > 0.4 ):
        return 1
    else:
        return 0
 
#--------------------------------------------------------------
##  TO PREPROCESS THE HTML PAGE BY REMOVING TAGS AND UNNECCESSARY CONTENT
#--------------------------------------------------------------
def getcontent( html ):
    html = re.sub( "&.*?;", "",html )
    raw = nltk.clean_html( html )
    raw = ' '.join( raw.split() )
    raw = re.sub( "\n","",raw )
    raw = re.sub( ' +',' ',raw )
    raw = re.sub( "[^\w]", " ",raw )

    for c in string.punctuation:
            raw = raw.replace( c,'' )
    #REMOVE NUMBERS
    for s in raw:
        if s.isdigit():
            raw = raw.replace( s, '' )
     
    return raw
        
#--------------------------------------------------------------
## MAIN METHOD
#--------------------------------------------------------------
def main():
    
    path = 'C:/Python27/html/kld/ns'    #   path to the folder stroing Spam or Non-Spam Pages. Change path accordingly when checking accuracy on Spam or Non Spam pages
    
    f = open('C:/Python27/html/stopword.txt') # stopwords.txt stores the list of stopwords
    # prepare the list of stopwords
    for line in f :    
        line = line[ 0:-1 ]
        stoplist.append( line )

    f.close()    
   #Read one webpage at a time and categorize it as Spam or Non-Spam
    for file in glob.glob( os.path.join( path, '*.htm*' ) ):
        a = []  
        temp = ''
        parenthtml = ""
        initialize()
        for line in open( file ):
            parenthtml += line       
    
        #--------------------------------------------------------------
        # Reading From Corpus And Removing HTML Tags and punctuations
        #------------------------------------------------------------- 
        a = getcontent(parenthtml)    
        a = ' '.join(a.split())
        totalwordsincludingstopwords = len(a.split())      

        print '##################################'
        print '-------------',(file.split('\\'))[1],'-------------'        
        fp.write( '---------------filename------>' )
        fp.write( (file.split('\\'))[1]+'---------------\n' )
        
        #--------------------------------------------------------------------------
        # Remove STOP WORDS and Lemmatize words
        #--------------------------------------------------------------------------               
        texts = []
        for word in a.split():
            if ( word not in stoplist and len(word)!=1 ):
                    word = lmtzr.lemmatize( word )
                    texts.append( word )        
       
        totalwordsexcludingstopwords = len( texts )
        tokensOnce = set( texts )     # get unique words
        totaluniquewords = len( tokensOnce )

        # If number of unique words % is (> 78 or < 20) then classify as Spam. The threshold values have been found by experiment
        if( totaluniquewords * 1.0 / totalwordsexcludingstopwords > 0.78  or totaluniquewords * 1.0 / totalwordsexcludingstopwords<0.20 ):

            print 'Unique words > 78% therefore Spam'
            fp.write( '\n'+'Unique words > 78% therefore Spam' )
            finalcategory = 'spam'    

        else:        
            result = 0            
            if( totalwordsincludingstopwords < 250 ):
                print( "Word Count less than 250" )
                
                # CALL POS Ratio Test
                result = POS_ratio( parenthtml )
                
                # if returned value i.e. result == 0 it implies the web page passed the POS Ratio Test, hence run the modified KLD test
                if(result == 0): 
                    # modified KLD TEST 
                    result = KLD( parenthtml )

                    # if result == 0 it implies web page passed even the modified KLD test and hence is Non-Spam
                    if(result == 0):                        
                        print 'non spam'
                        finalcategory = 'non spam'

                    else:                        
                        print 'spam'
                        finalcategory = 'spam'

                else:
                    print 'spam'
                    finalcategory = 'spam'
            
            else:

                dict = {}  # @ReservedAssignment
                occurencepercent = []
                print( "Word Count greater than 250" )
                # For each word calculate its Occurence percentage in the web page
                for word in tokensOnce:
                    count = 0
                    for compareword in texts:
                        if( word == compareword ):
                            count += 1

                    percentage = (count * 100.0) / totalwordsexcludingstopwords
                    occurencepercent.append( percentage ) 
                    dict[ word ] = float( percentage )
                 
                numberlessthan5 = 0     # stores number of words having occurence less than 5% in web page
                numberbetween5and10 = 0
                numbergreaterthan10 = 0                
                
                for w in dict:
                    per = dict[ w ]
                    
                    if( per < 5 ):
                        numberlessthan5 += 1
                        
                    elif( per >= 5.0 and per <= 10.0 ):
                        numberbetween5and10 += 1   
                         
                    elif( per > 10.0 ):
                        numbergreaterthan10 += 1
                    
                # Based on word frequency allot a category to the web page and based on the category alloted to the page run the sequence of tests on it.
                if( numberlessthan5 == totaluniquewords ):
                    print( "#category 1" )

                    #CALL POS Ratio Test
                    result = POS_ratio( parenthtml )

                    if( result == 0 ):
                        result = KLD( parenthtml )

                        if( result == 0 ):
                            print 'non spam'
                            finalcategory = 'non spam'
                        else:
                            print 'spam'
                            finalcategory = 'spam'
                        
                    else:
                        print 'spam'
                        finalcategory = 'spam'
                            
                elif( numberbetween5and10 >= 1 ):

                    print( "#category 2 " )
                    result = KLD(parenthtml)

                    if( result == 0) :
                        result = POS_ratio( parenthtml )

                        if( result == 0 ):
                            print 'non spam'
                            finalcategory = 'non spam'
                        else:
                            print 'spam'
                            finalcategory = 'spam'
                        
                    else:
                        print 'spam'
                        finalcategory = 'spam'
                                             
                elif( numbergreaterthan10 > 0 ):
                    # If page belongs to Category 3 then categorize it directly as Spam
                    print( "#category 3" )
                    print 'spam'
                    finalcategory = 'spam'                

        #WRITE TO FILE the result
        fp.write( '\n'+'category------>' )
        fp.write( finalcategory+'\n______________________________________________\n' )

    fp.close()
        
main()
