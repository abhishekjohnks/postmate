import { useEffect, useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileImage,
  FileText,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { api, download } from '../services/api';
import { ErrorBox, Loading, Modal } from './UI';

export default function DocumentPreview({ document, onClose }) {
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [state, setState] = useState({ url: null, pageCount: 1, loading: true, error: '' });
  const [downloadError, setDownloadError] = useState('');
  useEffect(() => {
    let live = true;
    let objectUrl;
    setState((s) => ({ ...s, url: null, loading: true, error: '' }));
    api(`/documents/${document.id}/preview?page=${page}`, { preview: true })
      .then(({ blob, pageCount }) => {
        if (!live) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ url: objectUrl, pageCount, loading: false, error: '' });
      })
      .catch((e) => live && setState((s) => ({ ...s, loading: false, error: e.message })));
    return () => {
      live = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [document.id, page]);
  const isPdf = document.content_type === 'application/pdf';
  return (
    <Modal title={`${document.kind.toUpperCase()} document preview`} onClose={onClose} wide>
      <div className="document-preview">
        <div className="preview-toolbar">
          <span className="preview-type">
            {isPdf ? <FileText size={17} /> : <FileImage size={17} />}{' '}
            {isPdf ? 'PDF document' : 'Image document'}
          </span>
          <div className="preview-tools">
            <button
              className="icon-button"
              aria-label="Zoom out"
              disabled={zoom <= 50}
              onClick={() => setZoom((z) => z - 25)}
            >
              <ZoomOut size={17} />
            </button>
            <span>{zoom}%</span>
            <button
              className="icon-button"
              aria-label="Zoom in"
              disabled={zoom >= 250}
              onClick={() => setZoom((z) => z + 25)}
            >
              <ZoomIn size={17} />
            </button>
            <button
              className="btn small"
              onClick={async () => {
                try {
                  await download(
                    `/documents/${document.id}`,
                    `${document.kind}.${isPdf ? 'pdf' : document.content_type === 'image/png' ? 'png' : 'jpg'}`,
                  );
                } catch (e) {
                  setDownloadError(e.message);
                }
              }}
            >
              <Download size={15} />
              Download
            </button>
          </div>
        </div>
        <ErrorBox error={state.error || downloadError} />
        <div className="preview-canvas">
          {state.loading ? (
            <Loading />
          ) : (
            state.url && (
              <img
                src={state.url}
                alt={`${document.kind.toUpperCase()} ${isPdf ? `page ${page}` : 'uploaded document'}`}
                style={{ width: `${zoom}%` }}
              />
            )
          )}
        </div>
        {isPdf && (
          <div className="preview-pagination">
            <button
              className="btn small"
              disabled={state.loading || page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft size={16} />
              Previous
            </button>
            <span>
              Page {page} of {state.pageCount}
            </span>
            <button
              className="btn small"
              disabled={state.loading || page >= state.pageCount}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight size={16} />
            </button>
          </div>
        )}
        <p className="preview-privacy">Private document · Visible only to authorized users</p>
      </div>
    </Modal>
  );
}
