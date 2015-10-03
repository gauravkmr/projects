import glob,os
from sklearn import svm
from sklearn.externals import joblib
from nltk.corpus import wordnet as wn


def main():
    feature_index={}
    total=0
    
    for line in open(os.getcwd()+'/features.txt',"r").read().split():
        feature_index[line]=total
        #print total,' ',line
        total=total+1

    length=len(feature_index)
    mapping = [0]*length
    print length
                     
    X=[]            #X holds feature vector mappings for each document
    y=[]            #hold class labels for training set

    fpath=open(os.getcwd()+'/training_set_path.txt')
 
    f = open('DMOZ_chi2_train.txt',"w")	

    class_no=0
    for line in fpath.read().split('\n'):
        print line
        path =line
	if path == '':
		break
        #print 'Path-----',path
	#print 'Glob',glob.glob(os.path.join(path,'*'))
        for file in glob.glob(os.path.join(path, '*')):
            #print file
            mapping = [0]*length
            for word in open(file).read().split():
		if len( word ) < 2 :
			continue
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
            y.append(class_no)

	    f.write(str(class_no))
	    f.write(" ")

	    for m in mapping:
		f.write(" ".join(str(m))+" ")

	    f.write('\n')
	

        class_no=class_no+1
    f.close()
    #print X
    #print y

    clf = svm.LinearSVC(dual=True,C=0.01 )

    #clf = svm.SVC(kernel='rbf',C=1) 
    clf.fit(X, y)
    
    joblib.dump(clf, 'svc_wordnet.pkl')

    import cPickle as pickle
    with open('data.p', 'wb') as fp:
        pickle.dump(feature_index, fp)

    with open('train_x.p', 'wb') as fp:
        pickle.dump(X, fp)
 
    with open('train_y.p', 'wb') as fp:
        pickle.dump(y, fp)
 
    
    '''path='C:/Python27/Training Set/Test/'
    for file in glob.glob(os.path.join(path, '*.txt')):
            print file
            mapping = [0]*length
            for word in open(file).read().split():
                index=feature_index.get(word)
                #print index
                if(index is not None):
                    mapping[index]=1
            print clf.predict(mapping)'''

main()
