import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MarkdownEditor({ value, onChange, placeholder = 'Write markdown...' }) {
  const [preview, setPreview] = useState(false);

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center border-b border-[#222222]">
        <button
          onClick={() => setPreview(false)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            !preview ? 'text-white bg-[#1a1a1a]' : 'text-[#888888] hover:text-white'
          }`}
        >
          Edit
        </button>
        <button
          onClick={() => setPreview(true)}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            preview ? 'text-white bg-[#1a1a1a]' : 'text-[#888888] hover:text-white'
          }`}
        >
          Preview
        </button>
      </div>

      {preview ? (
        <div className="p-4 prose-workify min-h-[300px]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {value || '*Nothing to preview*'}
          </ReactMarkdown>
        </div>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full min-h-[300px] p-4 bg-transparent text-white font-mono text-sm resize-y focus:outline-none placeholder-[#444444]"
        />
      )}
    </div>
  );
}
