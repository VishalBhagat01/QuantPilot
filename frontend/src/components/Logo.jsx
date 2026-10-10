import React from 'react';

/**
 * QuantPilot Logo Component
 * A premium, minimalist geometric SVG logo representing a Q and a P interlocking,
 * alongside a rising trend motif.
 */
export default function Logo({ size = 28, className = '' }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 100 100" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* 
        A highly polished abstract mark: 
        A continuous thick path that forms a minimalist Q and P, 
        giving an institutional, modern fintech vibe.
      */}
      
      {/* The main 'Q' shape with a gap */}
      <path 
        d="M 50 85 C 30.67 85 15 69.33 15 50 C 15 30.67 30.67 15 50 15 C 69.33 15 85 30.67 85 50 C 85 58.5 82 66.3 77 72.5" 
        stroke="white" 
        strokeWidth="12" 
        strokeLinecap="round" 
      />
      
      {/* The 'Q' tail functioning as an upward trend arrow */}
      <path 
        d="M 60 60 L 90 90" 
        stroke="white" 
        strokeWidth="14" 
        strokeLinecap="round" 
      />

      {/* The inner 'P' */}
      <path 
        d="M 35 30 L 35 70" 
        stroke="white" 
        strokeWidth="10" 
        strokeLinecap="round" 
      />
      <path 
        d="M 35 30 L 55 30 C 65 30 70 35 70 42.5 C 70 50 65 55 55 55 L 35 55" 
        stroke="white" 
        strokeWidth="10" 
        strokeLinecap="round" 
        strokeLinejoin="round" 
      />
      
      {/* Small accent dot for AI/Tech feel */}
      <circle cx="85" cy="25" r="7" fill="#FFE043" />
    </svg>
  );
}
