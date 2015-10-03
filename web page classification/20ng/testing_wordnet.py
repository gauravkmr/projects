import glob,os
from sklearn import svm
from sklearn.externals import joblib
import cPickle as pickle
from sklearn.metrics import classification_report
from sklearn import metrics
from nltk.corpus import wordnet as wn


from sklearn.metrics import zero_one_score
def main():


    clf=joblib.load('svc_wordnet.pkl')

    feature_index={}
    with open('data.p', 'rb') as fp:
        feature_index = pickle.load(fp)

    y_true=[]
    y_pred=[]

    X=[]
    
    fpath=open(os.getcwd()+'/testing_set_path.txt')
    f = open("20NG_ig_test.txt", "w")

    class_no=0
    
    for line in fpath.read().split('\n'):
        print line
        path =line
   	if path == '':
		break 
        for file in glob.glob(os.path.join(path, '*')):
            #print file
            mapping = [0]*2260
            for word in open(file).read().split():
                index=feature_index.get(word)
                        #print index
                if(index is not None):
                    mapping[index]=1
                else:
                    for ss in wn.synsets(word):
                        for l in ss.lemmas():
                            index = feature_index.get(l.name)
                            if(index is not None):
                                mapping[index]=1
                                break
                            
                    list = []
		    for syn_set in wn.synsets(word):
	                for syn in syn_set.lemmas():
                            list.append(syn.name)

                    for w in list:
                        index = feature_index.get(w)
                        if(index is not None):
                            mapping[index]=1
                            break
                        
            X.append(mapping)
            y_true.append(class_no)
            y_pred.append(int(clf.predict(mapping)))
            
	    f.write(str(class_no))
	    f.write(" ")
	    for m in mapping:
		f.write(str(m))
		f.write(" ")
	    f.write('\n')

        class_no=class_no+1

    f.close()

    with open('testing_X.p','wb') as fp:
	pickle.dump(X, fp)
    
    with open('testing_y_true.p','wb') as fp:
	pickle.dump(y_true, fp)

    with open('testing_y_pred.p','wb') as fp:
	pickle.dump(y_pred, fp)

    #print y_true
    #print y_pred
    target_names = ['Alt', 'Computers', 'Miscellaneous','Rec','Science','Social','Talk']
    print(classification_report(y_true, y_pred, target_names=target_names))
    accuracy = zero_one_score(y_true, y_pred)
    print 'accuracy',accuracy
    print metrics.precision_score(y_true, y_pred, average='macro')
    print metrics.recall_score(y_true, y_pred, average='micro')
    print metrics.f1_score(y_true, y_pred, average='weighted')  
main()
