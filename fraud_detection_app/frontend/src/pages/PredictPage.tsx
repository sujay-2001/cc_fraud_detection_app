/* src/pages/PredictPage.tsx — every numeric field mandatory */
import { useState, useRef } from "react";
import {
  MapContainer, TileLayer, Marker, Popup, useMapEvents,
} from "react-leaflet";
import type { LatLngTuple } from 'leaflet';
import { api } from "../lib/api";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

/* ---------- static option arrays ---------- */
const merchants = ["Cormier_LLC","Kilback_LLC","Kuhn_LLC","Schumm_PLC","Other"] as const;
const categories = [
  "food_dining","gas_transport","grocery_net","grocery_pos","health_fitness",
  "home","kids_pets","misc_net","misc_pos","personal_care",
  "shopping_net","shopping_pos","travel",
] as const;
const jobs = [
  "Analyst","Consultant","Creative","Engineer","Finance","Healthcare",
  "Legal","Manager","Officer","Other","Sales","Scientist","Teacher",
] as const;
const regions = ["Northeast","South","West"] as const;
const weekdays = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
  .map((l,i)=>({label:l,value:i}));                      // 0–6
const months = Array.from({length:12},(_,i)=>({
  value:i+1,
  label:new Date(0,i).toLocaleString("en",{month:"long"}),
}));

/* ---------- type helpers ---------- */
type PredictResponse = { fraud_probability:number; prediction:"fraud"|"not_fraud"; };
const f = (v:number|string)=>Number(v)+0.0;              // ensure float
const addOneHot = (arr:readonly string[], chosen:string, prefix:string, t:Record<string,unknown>) =>
  arr.forEach(v => t[`${prefix}${v}`] = v === chosen);

/* ---------- map picker component ---------- */
type PickerProps = {
  pos: LatLngTuple | null
  set: (lat: number, lng: number) => void
  /** if provided, will show this text in a Popup */
  label?: string
}

function Picker({ pos, set, label }: PickerProps) {
  // attach click handler exactly as before
  useMapEvents({
    click(e) {
      set(e.latlng.lat, e.latlng.lng)
    },
  })

  if (!pos) return null

  // now we wrap the Marker in a Popup if you gave us a label
  return (
    <Marker position={pos}>
      {label && <Popup>{label}</Popup>}
    </Marker>
  )
}

/* =================================================================== */
export default function PredictPage(){

  /* numeric state */
  const [amt,setAmt]   = useState("");        /* float */
  const [age,setAge]   = useState("");        /* int   */
  const [trx,setTrx]   = useState<[number,number]|null>(null);
  const [mer,setMer]   = useState<[number,number]|null>(null);
  const [hour,setHour] = useState("");
  const [dow,setDow]   = useState(0);
  const [mon,setMon]   = useState(1);

  /* categorical */
  const [merchant,setMerchant]=useState<typeof merchants[number]>("Cormier_LLC");
  const [category,setCategory]=useState<typeof categories[number]>("food_dining");
  const [job,setJob]         =useState<typeof jobs[number]>("Analyst");
  const [region,setRegion]   =useState<typeof regions[number]>("Northeast");
  const [gender,setGender]   =useState<"M"|"F">("M");

  /* raw JSON toggle */
  const [raw,setRaw]     = useState(false);
  const [jsonTxt,setTxt] = useState("");
  const [jsonErr,setJErr]= useState<string|null>(null);

  /* network */
  const [loading,setLoad] = useState(false);
  const [out,setOut]      = useState<PredictResponse|null>(null);
  const [fb,setFb]        = useState(false);

  /* refs for scrolling to missing control */
  const ageRef   = useRef<HTMLInputElement>(null);
  const amtRef   = useRef<HTMLInputElement>(null);
  const hourRef  = useRef<HTMLInputElement>(null);
  const trxRef   = useRef<HTMLDivElement>(null);
  const merRef   = useRef<HTMLDivElement>(null);

  /* ---------- build payload or throw ------------ */
  function build(){
    if(raw){
      try { setJErr(null); return JSON.parse(jsonTxt); }
      catch { setJErr("Invalid JSON"); throw Error(); }
    }

    /* client-side validation of every required field */
    if(!amt)  {amtRef.current?.focus(); throw Error();}
    if(!age)  {ageRef.current?.focus(); throw Error();}
    if(!hour) {hourRef.current?.focus();throw Error();}
    if(!trx)  {trxRef.current?.scrollIntoView({behavior:"smooth"}); throw Error();}
    if(!mer)  {merRef.current?.scrollIntoView({behavior:"smooth"}); throw Error();}

    const p:Record<string,unknown>={
      amt:f(amt), age:Number(age),
      lat:f(trx[0]), long:f(trx[1]),
      merch_lat:f(mer[0]), merch_long:f(mer[1]),
      tx_hour:Number(hour), tx_dayofweek:dow, tx_month:mon,
      gender_M:gender==="M",
    };
    addOneHot(merchants, merchant,"merchant_grouped_",p);
    addOneHot(categories,category,"category_",p);
    addOneHot(jobs,      job,     "job_grouped_",p);
    addOneHot(regions,   region,  "region_",p);

    return p;
  }

  /* ---------- submit ---------- */
  async function submit(e:React.FormEvent){
    e.preventDefault(); setOut(null); setFb(false);
    let pl; try{ pl=build(); }catch{return}   // stop on validation error
    setLoad(true);
    try{ const {data}=await api.post<PredictResponse>("/predict",pl); setOut(data); }
    finally{ setLoad(false); }
  }
  const feedback=(c:boolean)=>out&&api.post("/feedback",{prediction:out.prediction,correct:c})
      .then(()=>setFb(true)).catch(console.error);

  /* ---------- UI ---------- */
  return (
  <div className="space-y-6">
    <h2 className="text-xl font-semibold">Fraud prediction</h2>

    <label className="inline-flex items-center space-x-2">
      <input type="checkbox" checked={raw} onChange={()=>setRaw(!raw)}/>
      <span>Enter raw JSON instead</span>
    </label>

    {raw ? (
      <>
        <textarea rows={8} className="w-full border rounded p-2 font-mono"
          value={jsonTxt} onChange={e=>setTxt(e.target.value)}
          placeholder='{"amt":100.0,…}' />
        {jsonErr && <p className="text-sm text-red-600">{jsonErr}</p>}
        <button onClick={submit} className="bg-brand-blue text-white px-4 py-2 rounded">
          {loading?"Predicting…":"Predict"}
        </button>
      </>
    ) : (
    <form onSubmit={submit} className="space-y-6">

      {/* amount & age */}
      <div className="grid sm:grid-cols-2 gap-4">
        <input ref={amtRef} type="number" step="any" required value={amt}
          onChange={e=>setAmt(e.target.value)} placeholder="Amount *"
          className="border rounded p-2 w-full"/>
        <input ref={ageRef} type="number" min={0} required value={age}
          onChange={e=>setAge(e.target.value)} placeholder="Age *"
          className="border rounded p-2 w-full"/>
      </div>

      {/* maps */}
      <div className="grid md:grid-cols-2 gap-4">
        <section ref={trxRef}>
          <h3 className="font-medium mb-1">Transaction location *</h3>
          <MapContainer center={trx ?? [0,0]} zoom={2} className="h-48 w-full border rounded">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
            <Picker pos={trx} set={(la,ln)=>setTrx([la,ln])} label={`Selected at [${trx?.[0].toFixed(3)}, ${trx?.[1].toFixed(3)}]`}/>
          </MapContainer>
          {trx && <p className="text-xs">{trx.map(n=>n.toFixed(4)).join(", ")}</p>}
        </section>
        <section ref={merRef}>
          <h3 className="font-medium mb-1">Merchant location *</h3>
          <MapContainer center={mer ?? [0,0]} zoom={2} className="h-48 w-full border rounded">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
            <Picker pos={mer} set={(la,ln)=>setMer([la,ln])} label={`Selected at [${mer?.[0].toFixed(3)}, ${mer?.[1].toFixed(3)}]`}/>
          </MapContainer>
          {mer && <p className="text-xs">{mer.map(n=>n.toFixed(4)).join(", ")}</p>}
        </section>
      </div>

      {/* time */}
      <div className="grid sm:grid-cols-3 gap-4">
        <input ref={hourRef} type="number" min={0} max={23} required value={hour}
          onChange={e=>setHour(e.target.value)} placeholder="Hour (0-23) *"
          className="border rounded p-2"/>
        <select value={dow} onChange={e=>setDow(+e.target.value)} className="border rounded p-2">
          {weekdays.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={mon} onChange={e=>setMon(+e.target.value)} className="border rounded p-2">
          {months.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* categorical dropdowns */}
      <div className="grid sm:grid-cols-2 gap-4">
        <select className="border rounded p-2" value={merchant} onChange={e=>setMerchant(e.target.value as any)}>
          <option value="">Select merchant</option>
          {merchants.map(m=><option key={m}>{m}</option>)}
        </select>
        <select className="border rounded p-2" value={category} onChange={e=>setCategory(e.target.value as any)}>
          <option value="">Select transaction category</option>
          {categories.map(c=><option key={c}>{c}</option>)}
        </select>
        <select className="border rounded p-2" value={job} onChange={e=>setJob(e.target.value as any)}>
          <option value="">Select cardholder's job</option>
          {jobs.map(j=><option key={j}>{j}</option>)}
        </select>
        <select className="border rounded p-2" value={region} onChange={e=>setRegion(e.target.value as any)}>
          <option value="">Select region</option>
          {regions.map(r=><option key={r}>{r}</option>)}
        </select>
      </div>

      {/* gender */}
      <div className="flex space-x-4">
        {["M","F"].map(g=>(
          <button key={g} type="button"
            className={`px-4 py-2 border rounded ${gender===g?"bg-brand-blue text-white":""}`}
            onClick={()=>setGender(g as "M"|"F")}
          >{g==="M"?"Male":"Female"}</button>
        ))}
      </div>

      <button type="submit" disabled={loading}
        className="bg-brand-blue text-white rounded px-6 py-2">
        {loading?"Predicting…":"Predict"}
      </button>
    </form>
    )}

    {/* result */}
    {out && (
      <div className="mt-6 space-y-3">
        <p>Fraud probability: <strong>{(out.fraud_probability*100).toFixed(1)}%</strong></p>
        <p>
          Prediction:&nbsp;
          <strong className={out.prediction==="fraud"?"text-red-600":"text-green-600"}>
            {out.prediction==="fraud"?"Fraud":"Not Fraud"}
          </strong>
        </p>
        {!fb ? (
          <div className="space-x-3">
            <span>Was this correct?</span>
            <button onClick={()=>feedback(true)}  className="px-3 py-1 bg-green-600 text-white rounded">Yes</button>
            <button onClick={()=>feedback(false)} className="px-3 py-1 bg-red-600 text-white rounded">No</button>
          </div>
        ) : <p className="text-xs text-gray-500">Thanks for your feedback!</p>}
      </div>
    )}
  </div>);
}
