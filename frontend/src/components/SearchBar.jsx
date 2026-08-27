import { useState } from "react";
import { Search } from "lucide-react";

export default function SearchBar({ onSearch, placeholder = "Enter vehicle number (e.g. TN09AB1234)" }) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <div className="flex-1 relative">
        <Search
          size={18}
          className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          placeholder={placeholder}
          className="w-full bg-[#111827] border border-white/[0.08] rounded-lg pl-11 pr-4 py-2.5 text-[14px] text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/40 focus:ring-1 focus:ring-blue-500/20 font-mono tracking-wide transition-colors"
        />
      </div>
      <button
        type="submit"
        className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-lg text-[13px] font-medium transition-colors"
      >
        Search
      </button>
    </form>
  );
}
