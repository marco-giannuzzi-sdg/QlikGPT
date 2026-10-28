import { useElement, useLayout, useApp, useEffect, useState, useMemo } from '@nebula.js/stardust';
import { cube, measureIds, sessionDefinitions } from './data.mjs';
import { renderDashboard } from './render.mjs';
import css from './styles.js';

export default function supernova() {
  return {
    qae: {
      properties: { showTitles: false, qHyperCubeDef: cube(measureIds) },
      data: { targets: [{ path: '/qHyperCubeDef', dimensions: { min: 0, max: 0 },
        measures: { min: 4, max: 4 } }] },
    },
    ext: { definition: { type: 'items', component: 'accordion',
      items: { settings: { uses: 'settings' } } },
      support: { snapshot: false, export: false, exportData: true, viewData: true } },
    component() {
      const element = useElement(), app = useApp(), layout = useLayout();
      const [state, setState] = useState({});
      const models = useMemo(() => new Map(), []);
      const id = useMemo(() => 'qgp-' + Math.random().toString(36).slice(2), []);
      useEffect(() => {
        if (!app) return undefined;
        let disposed = false;
        const resources = [];
        const fail = () => { if(!disposed) setState(prev=>({...prev,error:'Impossibile aggiornare i dati Qlik. Riaprire il foglio per riconnettersi.'})); };
        for (const def of sessionDefinitions()) {
          app.createSessionObject(def.props).then(async model => {
            const info = await model.getInfo();
            if(disposed) { await app.destroySessionObject(info.qId); return; }
            models.set(def.key, model);
            let serial=0;
            const update=async()=>{
              const request=++serial;
              try{
                const next=await model.getLayout();
                if(!disposed && request===serial) setState(prev=>({...prev,[def.key]:next}));
              }catch { fail(); }
            };
            resources.push({model,info,update});
            model.on('changed',update);
            await update();
          }).catch(fail);
        }
        return () => {
          disposed=true;
          resources.forEach(({model,info,update})=>{
            model.removeListener('changed',update);
            app.destroySessionObject(info.qId).catch(()=>{});
          });
          models.clear();
        };
      }, [app]);
      useEffect(() => {
        element.innerHTML='<style>'+css+'</style><div class="qgp">'+renderDashboard(layout,state,id)+'</div>';
        const fail=()=>setState(prev=>({...prev,error:'Selezione non applicata. Riprovare.'}));
        const change=event=>{
          const target=event.target.closest('[data-filter]');
          if(!target)return;
          const model=models.get(target.dataset.filter);
          if(!model)return;
          const action=target.value==='' ? model.clearSelections('/qListObjectDef')
            : model.selectListObjectValues('/qListObjectDef',[Number(target.value)],false);
          action.catch(fail);
        };
        const activate=event=>{
          if(event.type==='keydown' && !['Enter',' '].includes(event.key))return;
          const target=event.target.closest('[data-reset],[data-market],[data-trend]');
          if(!target)return;
          if(event.type==='keydown'){ if(target.tagName==='BUTTON')return; event.preventDefault(); }
          let action;
          if(target.hasAttribute('data-reset')) action=app.clearAll();
          else{
            const key=target.hasAttribute('data-market')?'markets':'trend';
            const elem=Number(target.dataset.market ?? target.dataset.trend);
            action=models.get(key)?.selectHyperCubeValues('/qHyperCubeDef',0,[elem],true);
          }
          action?.catch(fail);
        };
        element.addEventListener('change',change);
        element.addEventListener('click',activate);
        element.addEventListener('keydown',activate);
        return ()=>{
          element.removeEventListener('change',change);
          element.removeEventListener('click',activate);
          element.removeEventListener('keydown',activate);
        };
      }, [element,layout,state,app]);
    },
  };
}
