import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "en" | "hi";

/**
 * EN/HI toggle for customer-facing screens (Hindi in Devanagari + Hinglish flavor).
 * Analyst screens stay in English.
 */
const STRINGS = {
  en: {
    appTagline: "Payment Safety Check",
    recentPayments: "Recent payments",
    checkinTitle: "A quick check about a recent payment",
    checkinQuestion: "Did someone pressure you or rush you to make this payment?",
    yes: "Yes",
    no: "No",
    unsure: "Not sure",
    checkinSub: "Your answer helps us support you. We never accuse anyone.",
    thanks: "Thank you. We're sorry this happened.",
    nextStepsTitle: "What happens next",
    nextSteps1: "Your report will be prepared with your confirmation. You review and approve it before it is sent.",
    nextSteps2: "You can call 1930 (national cyber helpline) or report at cybercrime.gov.in — we never auto-submit without your approval.",
    nextSteps3: "Keep any messages, call logs or screenshots as evidence.",
    intakeTitle: "Help us build your report",
    reportApprove: "I have checked these details and they are correct.",
    submitReport: "Submit report",
    reportSubmitted: "Report submitted",
    referenceId: "Reference ID",
    hindi: "हिंदी",
    english: "English",
  },
  hi: {
    appTagline: "भुगतान सुरक्षा जाँच",
    recentPayments: "हाल के भुगतान",
    checkinTitle: "हाल के एक भुगतान के बारे में एक छोटी जाँच",
    checkinQuestion: "क्या किसी ने आपको दबाव डालकर या जल्दी में यह भुगतान करने को कहा?",
    yes: "हाँ",
    no: "नहीं",
    unsure: "पता नहीं",
    checkinSub: "आपका जवाब हमें आपकी मदद करने में मदद करता है। हम किसी पर आरोप नहीं लगाते।",
    thanks: "धन्यवाद। हमें खेद है कि ऐसा हुआ।",
    nextStepsTitle: "आगे क्या होगा",
    nextSteps1: "आपकी पुष्टि के साथ रिपोर्ट तैयार होगी। भेजने से पहले आप उसे देखकर मंज़ूरी देंगे।",
    nextSteps2: "आप 1930 (राष्ट्रीय साइबर हेल्पलाइन) पर कॉल कर सकते हैं या cybercrime.gov.in पर रिपोर्ट कर सकते हैं — आपकी मंज़ूरी के बिना कुछ नहीं भेजा जाएगा।",
    nextSteps3: "सबूत के लिए मैसेज, कॉल लॉग या स्क्रीनशॉट संभालकर रखें।",
    intakeTitle: "रिपोर्ट बनाने में हमारी मदद करें",
    reportApprove: "मैंने ये विवरण देख लिए हैं और वे सही हैं।",
    submitReport: "रिपोर्ट भेजें",
    reportSubmitted: "रिपोर्ट भेज दी गई",
    referenceId: "संदर्भ संख्या",
    hindi: "हिंदी",
    english: "English",
  },
} as const;

type StringKey = keyof typeof STRINGS.en;

const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: StringKey) => string }>({
  lang: "en",
  setLang: () => {},
  t: (k) => String(k),
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem("scam-report-lang") === "hi" ? "hi" : "en"));
  useEffect(() => {
    localStorage.setItem("scam-report-lang", lang);
    document.documentElement.lang = lang === "hi" ? "hi" : "en";
  }, [lang]);
  return (
    <LangContext.Provider value={{ lang, setLang, t: (k) => STRINGS[lang][k] }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
