# Devanagari -> readable English: dictionary of known terms first, then syllabic transliteration.
import re

DEVA = lambda c: '\u0900' <= c <= '\u097f'

CONS={'क':'k','ख':'kh','ग':'g','घ':'gh','ङ':'ng','च':'ch','छ':'chh','ज':'j','झ':'jh','ञ':'ny',
'ट':'t','ठ':'th','ड':'d','ढ':'dh','ण':'n','त':'t','थ':'th','द':'d','ध':'dh','न':'n',
'प':'p','फ':'ph','ब':'b','भ':'bh','म':'m','य':'y','र':'r','ल':'l','व':'v','श':'sh','ष':'sh',
'स':'s','ह':'h','क्ष':'ksh','त्र':'tr','ज्ञ':'gy','ळ':'l','ऱ':'r','ड़':'r','ढ़':'rh','फ़':'f','ज़':'z','क़':'q','ख़':'kh','ग़':'g'}
IVOW={'अ':'a','आ':'a','इ':'i','ई':'i','उ':'u','ऊ':'u','ऋ':'ri','ए':'e','ऐ':'ai','ओ':'o','औ':'au','ऍ':'e','ऑ':'o'}
MATRA={'ा':'a','ि':'i','ी':'i','ु':'u','ू':'u','ृ':'ri','े':'e','ै':'ai','ो':'o','ौ':'au','ॅ':'e','ॉ':'o'}
SIGN={'ं':'n','ँ':'n','ः':'h','ॐ':'om','।':'.','॥':'.','ऽ':''}
DIG={'०':'0','१':'1','२':'2','३':'3','४':'4','५':'5','६':'6','७':'7','८':'8','९':'9'}
HALANT='्'; NUKTA='़'

def translit(s):
    out=[]; i=0; n=len(s)
    while i<n:
        ch=s[i]
        # two-char conjuncts handled by base loop via halant; just map singles
        if ch in CONS:
            base=CONS[ch]; j=i+1
            if j<n and s[j]==NUKTA: j+=1
            if j<n and s[j]==HALANT:
                out.append(base); i=j+1; continue
            if j<n and s[j] in MATRA:
                out.append(base+MATRA[s[j]]); i=j+1; continue
            # inherent 'a' unless word-final (schwa deletion)
            nxt=s[j] if j<n else ''
            if nxt=='' or not DEVA(nxt):
                out.append(base)          # drop final schwa: राम->ram, संजिव->sanjiv
            else:
                out.append(base+'a')
            i=j; continue
        if ch in IVOW: out.append(IVOW[ch]); i+=1; continue
        if ch in MATRA: out.append(MATRA[ch]); i+=1; continue
        if ch in SIGN: out.append(SIGN[ch]); i+=1; continue
        if ch in DIG: out.append(DIG[ch]); i+=1; continue
        if ch==HALANT or ch==NUKTA: i+=1; continue
        out.append(ch); i+=1
    w=''.join(out)
    return w[:1].upper()+w[1:] if w else w

# Known terms -> authoritative English (from the site's own English labels + standard spellings)
DICT={
'गण्डकी':'Gandaki','बागमती':'Bagmati','कोशी':'Koshi','लुम्बिनी':'Lumbini','कर्णाली':'Karnali',
'सुदूरपश्चिम':'Sudurpashchim','मधेश':'Madhesh','प्रदेश':'Province',
'रसुवा':'Rasuwa','रसुवागढी':'Rasuwagadhi','नुवाकोट':'Nuwakot','त्रिशुली':'Trishuli','धादिङ':'Dhading',
'चितवन':'Chitwan','नवलपरासी':'Nawalparasi','भरतपुर':'Bharatpur','काठमाडौं':'Kathmandu','काठमाण्डौं':'Kathmandu',
'सिन्धुपाल्चोक':'Sindhupalchok','गोरखा':'Gorkha','रामेछाप':'Ramechhap','बर्दघाट':'Bardaghat','सुस्ता':'Susta',
'गैंडाकोट':'Gaindakot','गैँडाकोट':'Gaindakot','मध्यविन्दु':'Madhyabindu','मध्यबिन्दु':'Madhyabindu','मध्येविन्दु':'Madhyabindu',
'टिमुरे':'Timure','स्याफ्रुबेसी':'Syabrubesi','स्याफ्रुबेशी':'Syabrubesi','स्याफ्रुवेशी':'Syabrubesi','स्याफ्रु':'Syabru',
'धुन्चे':'Dhunche','बेत्रावती':'Betrawati','वेत्रवती':'Betrawati','बट्टार':'Battar','कालिकास्थान':'Kalikasthan',
'हाकुबेशी':'Hakubesi','हाकुबेसी':'Hakubesi','चिलिमे':'Chilime','मैलुङ':'Mailung','कोलनी':'Kolani',
'मानेढुङ्गा':'Manedhunga','सलिटार':'Salitar','तुप्चे':'Tupche','शिवपुरी':'Shivapuri','बिदुर':'Bidur',
'गल्छी':'Galchhi','धैबुङ':'Dhaibung','शान्ति':'Shanti','बजार':'Bazar','धुन्चे':'Dhunche','बझाङ':'Bajhang',
'महत्तरी':'Mahottari','रौतहट':'Rautahat','महानगरपालिका':'Metropolitan City','उपमहानगरपालिका':'Sub-Metropolitan City',
'नगरपालिका':'Municipality','गाउँपालिका':'Rural Municipality','अस्पताल':'Hospital','प्रादेशिक':'Provincial',
'जिल्ला':'District','वडा':'Ward','विदेशी':'Foreign','भारत':'India','चीन':'China','चैनई':'Chennai','देश':'Country',
'ठेगाना':'Address','नखुलेको':'Unknown','पूर्व':'East','पश्चिम':'West','उत्तर':'North','दक्षिण':'South',
'रहेको':'','बजे':'','उमेर':'Age','प्रहरी':'Police','कुमार':'Kumar','कुमारी':'Kumari','सिंह':'Singh','तामाङ':'Tamang',
'श्रेष्ठ':'Shrestha','बाढी':'flood','पहिरो':'landslide','पहिरोमा':'landslide','मृत्यू':'death','मृत्यु':'death','बेबारिसे':'unclaimed','बेवारिसे':'unclaimed','फेला':'found','परेको':'','गते':'','मिति':'Date','देखिने':'appearing','जस्तो':'like','आएको':'came','परी':'','भएको':'','अं':'approx.','सम्बन्धित':'related','पहिचान':'identity','शवहरूको':'of bodies','जिल्लामा':'district','दायाँ':'right','बायाँ':'left','हातमा':'on hand','खुट्टामा':'on leg','विवाहित':'Married','अविवाहित':'Unmarried','हिन्दु':'Hindu','बौद्ध':'Buddhist','इस्लाम':'Muslim','किराँत':'Kirat','इसाई':'Christian','उचाई':'Height','उचाइ':'Height','कद':'Height','हुलिया':'Description','वर्ण':'Complexion','रंग':'Colour','कपडा':'Clothes','लगाएको':'Wearing','पहिरन':'Attire','कमिज':'Shirt','सर्ट':'Shirt','पाइन्ट':'Pants','पेन्ट':'Pants','सुरुवाल':'Trousers','साडी':'Saree','कुर्ता':'Kurta','ज्याकेट':'Jacket','स्विटर':'Sweater','टिसर्ट':'T-shirt','जुत्ता':'Shoes','चप्पल':'Slippers','खत':'Scar','चिन्ह':'Mark','दाग':'Mark','तिल':'Mole','ट्याटु':'Tattoo','पोतो':'Tattoo','कपाल':'Hair','दाह्री':'Beard','जुँगा':'Moustache','आँखा':'Eyes','नाक':'Nose','कान':'Ear','दाँत':'Teeth','हात':'Hand','खुट्टा':'Leg','गहुँगोरो':'Wheatish','गोरो':'Fair','कालो':'Black','सेतो':'White','रातो':'Red','निलो':'Blue','हरियो':'Green','खैरो':'Brown','पहेंलो':'Yellow','अग्लो':'Tall','होचो':'Short','मोटो':'Heavy','दुब्लो':'Thin','ज्यान':'Body','वर्ष':'Years','फिट':'Feet','इन्च':'Inch','किलो':'kg','से.मी':'cm','से.मि':'cm','पुरुष':'Male','महिला':'Female','बालक':'Boy','बालिका':'Girl','अनुमानित':'Approx','हाल':'Current','शव':'body','राखेको':'kept at','स्थान':'location','अवस्था':'condition','विपद्':'disaster','विपद':'disaster','मृतक':'deceased','घाइते':'injured','उद्धार':'rescued','सकिएको':'','गरिएको':'','ठाकुर':'Thakur','यादव':'Yadav','चौधरी':'Chaudhary','गुप्ता':'Gupta','शाह':'Shah','साह':'Sah',
}

_keys=sorted(DICT.keys(), key=len, reverse=True)

def to_english(text):
    if not text: return text
    # apply dictionary (longest terms first)
    for k in _keys:
        if k in text:
            text=text.replace(k, ' '+DICT[k]+' ')
    # transliterate any remaining Devanagari runs
    def repl(m): return translit(m.group(0))
    text=re.sub(r'[\u0900-\u097f]+', repl, text)
    text=re.sub(r'\s+',' ',text).strip(' ,')
    return text

if __name__=='__main__':
    tests=['संजिव पौडेल','राम','सीता','स्याफ्रुबेसी','गैंडाकोट','मोनिका जैन','संजीव जैन',
           'गण्डकी प्रदेश, नवलपरासी बर्दघाट सुस्ता पूर्व, मध्यविन्दु नगरपालिका- १२',
           'विदेशी, Address: भारत','हाल शव राखेको स्थान: मध्यबिन्दु प्रादेशिक अस्पताल']
    for t in tests: print(t,'  ->  ',to_english(t))
