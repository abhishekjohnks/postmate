import { useEffect, useState } from 'react';
import { api } from '../services/api';
export function useData(path, revision = 0) {
  const [state, setState] = useState({ data: null, loading: true, error: '' });
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const update = () => setRefresh((value) => value + 1);
    window.addEventListener('postmate:records-changed', update);
    const timer = path.startsWith('/notifications') ? setInterval(update, 60000) : null;
    return () => {
      window.removeEventListener('postmate:records-changed', update);
      if (timer) clearInterval(timer);
    };
  }, [path]);
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: '' }));
    api(path)
      .then((data) => live && setState({ data, loading: false, error: '' }))
      .catch((e) => live && setState({ data: null, loading: false, error: e.message }));
    return () => {
      live = false;
    };
  }, [path, revision, refresh]);
  return state;
}
