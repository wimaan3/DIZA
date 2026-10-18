import {useEffect,useState} from 'react';
import {DEMO,validateOps} from './data.js';
export function useOps(mode,token,retry) {
  const [state,setState]=useState({data:null,error:'',updated:null,loading:false});
  useEffect(()=>{
    if(mode!=='live') {setState({data:null,error:'',updated:null,loading:false});return;}
    let active=true, timer;
    const controller=new AbortController();
    setState({data:null,error:'',updated:null,loading:true});
    async function poll() {
      let timeout;
      try {
        const requestController=new AbortController();
        const abort=()=>requestController.abort();
        controller.signal.addEventListener('abort',abort,{once:true});
        timeout=setTimeout(abort,10000);
        let response;
        try { response=await fetch('/api/ops',{headers:token?{Authorization:`Bearer ${token}`}:{},signal:requestController.signal,cache:'no-store'}); }
        finally {controller.signal.removeEventListener('abort',abort);}
        if(response.status===401 || response.status===403) {
          if(active) setState({data:null,error:'Operator access required. Enter the backend operator token to connect.',updated:null,loading:false});
          return; // Retry only after the operator changes credentials.
        }
        if(!response.ok) throw new Error(`Backend unavailable (${response.status}).`);
        const data=validateOps(await response.json());
        if(active) setState({data,error:'',updated:new Date(),loading:false});
      } catch(e) {
        if(active) setState(s=>({...s,error:e.name==='AbortError'?'Backend request timed out.':e.message,loading:false}));
      } finally {clearTimeout(timeout);}
      if(active) timer=setTimeout(poll,5000);
    }
    poll();
    return ()=>{active=false;controller.abort();clearTimeout(timer);};
  },[mode,token,retry]);
  return mode==='demo'?{data:DEMO,error:'',updated:null,loading:false}:state;
}
