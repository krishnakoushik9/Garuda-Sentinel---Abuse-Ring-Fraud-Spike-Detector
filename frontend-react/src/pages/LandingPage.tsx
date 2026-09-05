import { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield,
  ArrowRight,
  X,
  Check,
  Cpu,
  Fingerprint,
  Zap,
  Globe,
  Menu,
  ArrowUpRight
} from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import GooeyNav from '@/components/ui/GooeyNav';

export default function LandingPage() {
  const navigate = useNavigate();
  const enterPlatform = useAppStore((s) => s.enterPlatform);
  const problemRef = useRef<HTMLDivElement>(null);

  // Responsive state for mobile navigation
  const [isMobile, setIsMobile] = useState(false);
  
  // Parallax mouse position state
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Video Ref & Audio & Fade states
  // Video & Overlay Refs & audio states
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [isMuted, setIsMuted] = useState(false); // Play audio by default
  const requestRef = useRef<number | null>(null);

  // Custom cursor position and hover state
  const [cursorPos, setCursorPos] = useState({ x: -100, y: -100 });
  const [isHoveringBtn, setIsHoveringBtn] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || window.innerWidth < 1024) return;
    const moveCursor = (e: MouseEvent) => {
      setCursorPos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', moveCursor);
    return () => window.removeEventListener('mousemove', moveCursor);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || window.innerWidth < 768) return;

    const handleMouseMove = (e: MouseEvent) => {
      // Divisor is 350 for 2-3px shift max to make movement extremely subtle
      const x = (e.clientX - window.innerWidth / 2) / 350;
      const y = (e.clientY - window.innerHeight / 2) / 350;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // requestAnimationFrame loop to track currentTime with millisecond precision
  // and handle super-smooth 60fps/120fps direct DOM opacity and volume fade.
  useEffect(() => {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video) return;

    const fadeTime = 3.0; // 3.0s slow and soft transition fade duration

    const tick = () => {
      if (!video || !overlay) {
        requestRef.current = requestAnimationFrame(tick);
        return;
      }

      const duration = video.duration;
      const currentTime = video.currentTime;

      if (duration) {
        let opacity = 0;

        if (currentTime > duration - fadeTime) {
          // Fade to black at the end
          const ratio = (currentTime - (duration - fadeTime)) / fadeTime;
          const normalizedRatio = Math.min(1, Math.max(0, ratio));
          // Smooth cosine interpolation
          opacity = 0.5 - 0.5 * Math.cos(normalizedRatio * Math.PI);
        } else if (currentTime < fadeTime) {
          // Fade in from black at the beginning
          const ratio = currentTime / fadeTime;
          const normalizedRatio = Math.min(1, Math.max(0, ratio));
          // Smooth cosine interpolation
          opacity = 0.5 + 0.5 * Math.cos(normalizedRatio * Math.PI);
        } else {
          opacity = 0;
        }

        // Bypassing React virtual DOM/reconciliation entirely for 120fps hardware-accelerated precision
        overlay.style.opacity = opacity.toString();

        // Audio fade synchronization
        if (!isMuted) {
          video.muted = false;
          video.volume = Math.max(0, Math.min(1, 1 - opacity));
        } else {
          video.muted = true;
          video.volume = 0;
        }
      }

      requestRef.current = requestAnimationFrame(tick);
    };

    requestRef.current = requestAnimationFrame(tick);
    return () => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
    };
  }, [isMuted]);

  // Handle browser auto-play restrictions on audio
  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.muted = isMuted;
      video.play().catch((err) => {
        console.log("Autoplay with audio blocked. Falling back to muted play.", err);
        setIsMuted(true);
        video.muted = true;
        video.play().catch((e) => console.log("Muted autoplay also blocked:", e));
      });
    }
  }, [isMuted]);

  const handleVideoEnded = () => {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (video) {
      video.currentTime = 0;
      if (!isMuted) {
        video.muted = false;
        video.volume = 0;
      }
      if (overlay) {
        overlay.style.opacity = "1";
      }
      video.play().catch((err) => console.log("Loop replay failed:", err));
    }
  };

  const handleLaunch = () => {
    enterPlatform();
    navigate('/dashboard');
  };

  const scrollToProblem = () => {
    problemRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToFeatures = () => {
    const featElement = document.getElementById('features');
    featElement?.scrollIntoView({ behavior: 'smooth' });
  };

  // Ease Out Cubic custom Bezier curve cast to any to satisfy Framer Motion's strict type checker
  const easeTransition = [0.22, 1, 0.36, 1] as any;

  const navItems = [
    { 
      label: "Home", 
      href: "#", 
      onClick: (e: React.MouseEvent<HTMLAnchorElement>) => { 
        e.preventDefault(); 
        window.scrollTo({ top: 0, behavior: 'smooth' }); 
      } 
    },
    { 
      label: "Features", 
      href: "#features", 
      onClick: (e: React.MouseEvent<HTMLAnchorElement>) => { 
        e.preventDefault(); 
        scrollToFeatures(); 
      } 
    },
    { 
      label: isMobile ? "Flow" : "How It Works", 
      href: "#how-it-works", 
      onClick: (e: React.MouseEvent<HTMLAnchorElement>) => { 
        e.preventDefault(); 
        const el = document.getElementById('how-it-works'); 
        el?.scrollIntoView({ behavior: 'smooth' }); 
      } 
    },
    { 
      label: isMobile ? "Launch" : "Workstation", 
      href: "#", 
      onClick: (e: React.MouseEvent<HTMLAnchorElement>) => { 
        e.preventDefault(); 
        handleLaunch(); 
      } 
    }
  ];

  return (
    <div className="landing-root min-h-screen bg-[#F7FAF8] font-sans text-[#0D1117] selection:bg-[#14D86F]/20 selection:text-[#0D1117] overflow-x-hidden">
      
      {/* Custom Cursor Glow (Desktop Only) */}
      <div 
        className="hidden lg:block pointer-events-none fixed top-0 left-0 -translate-x-1/2 -translate-y-1/2 rounded-full blur-xl bg-[#14D86F]/12 transition-all duration-300 ease-out z-[9999]"
        style={{
          left: `${cursorPos.x}px`,
          top: `${cursorPos.y}px`,
          width: isHoveringBtn ? '95px' : '45px',
          height: isHoveringBtn ? '95px' : '45px',
        }}
      />

      {/* Audio Toggle Button */}
      <motion.button
        onClick={() => setIsMuted(!isMuted)}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center w-12 h-12 bg-white/70 backdrop-blur-md border border-white/40 rounded-full shadow-[0_8px_32px_0_rgba(0,0,0,0.08)] text-[#0D1117] cursor-pointer hover:bg-white/90 transition-colors duration-200"
        title={isMuted ? "Play Audio" : "Mute Audio"}
        onMouseEnter={() => setIsHoveringBtn(true)}
        onMouseLeave={() => setIsHoveringBtn(false)}
      >
        {isMuted ? (
          <svg className="w-5 h-5 text-[#5E6C76]" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 9.75L19.5 12m0 0l2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6L4.5 9H1.5v6h3l4.5 3.75V5.25z" />
          </svg>
        ) : (
          <div className="flex items-end gap-[3px] h-4">
            <span className="w-[3px] bg-[#14D86F] rounded-full animate-[soundWave_0.8s_ease-in-out_infinite_alternate]" style={{ height: '60%' }} />
            <span className="w-[3px] bg-[#14D86F] rounded-full animate-[soundWave_0.5s_ease-in-out_infinite_alternate]" style={{ height: '100%', animationDelay: '0.15s' }} />
            <span className="w-[3px] bg-[#14D86F] rounded-full animate-[soundWave_0.7s_ease-in-out_infinite_alternate]" style={{ height: '40%', animationDelay: '0.3s' }} />
            <span className="w-[3px] bg-[#14D86F] rounded-full animate-[soundWave_0.6s_ease-in-out_infinite_alternate]" style={{ height: '80%', animationDelay: '0.05s' }} />
          </div>
        )}
      </motion.button>

      {/* ────────────────────────────────────────────────────────
         FLOATING GOOEY NAVBAR
         ──────────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: easeTransition, delay: 0.0 }}
        className="fixed top-10 left-1/2 -translate-x-1/2 z-50 py-1.5 px-2"
        style={{
          background: 'rgba(13, 17, 23, 0.85)',
          backdropFilter: 'blur(28px) saturate(180%)',
          WebkitBackdropFilter: 'blur(28px) saturate(180%)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 12px 40px rgba(0, 0, 0, 0.25)',
          borderRadius: '999px',
        }}
      >
        <GooeyNav
          items={navItems}
          particleCount={12}
          particleDistances={[80, 10]}
          particleR={80}
          initialActiveIndex={0}
          animationTime={500}
          timeVariance={200}
          colors={[1, 2, 3, 1, 2, 3, 1, 4]}
        />
      </motion.div>


      {/* ────────────────────────────────────────────────────────
         HERO SECTION (100vh)
         ──────────────────────────────────────────────────────── */}
      <section className="relative w-full h-screen flex items-center justify-center overflow-hidden">
        
        {/* Background Looping Cover Video */}
        <div className="absolute inset-0 w-full h-full z-0 overflow-hidden">
          <motion.video
            ref={videoRef}
            src="/Futuristic.mp4"
            autoPlay
            playsInline
            preload="auto"
            onEnded={handleVideoEnded}
            className="absolute inset-0 w-full h-full object-cover origin-center"
            initial={{ scale: 1.0 }}
            animate={{ scale: [1.0, 1.05, 1.0] }}
            transition={{
              duration: 30,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          {/* Smooth black overlay for loop transition */}
          <div 
            ref={overlayRef}
            className="absolute inset-0 pointer-events-none"
            style={{ 
              opacity: 1, 
              zIndex: 2, 
              backgroundColor: '#000000' 
            }}
          />
          
          {/* Ambient UI Overlay: Subtle radial gradient behind hero text for enhanced readability */}
          <div 
            className="absolute inset-0 pointer-events-none"
            style={{
              zIndex: 2,
              background: 'radial-gradient(circle at center, rgba(255,255,255,0.30), rgba(255,255,255,0.10), transparent 70%)',
            }}
          />

          {/* Decorative UI elements: Floating glowing objects in background */}
          {/* Ring */}
          <div 
            className="absolute top-[18%] right-[12%] w-36 h-36 border border-[#14D86F]/10 rounded-full animate-spin-slow pointer-events-none"
            style={{ zIndex: 2 }}
          />
          {/* Glowing dot 1 */}
          <div 
            className="absolute top-[28%] left-[14%] w-2.5 h-2.5 bg-[#14D86F]/15 rounded-full blur-[2px] animate-float pointer-events-none"
            style={{ zIndex: 2 }}
          />
          {/* Glowing dot 2 */}
          <div 
            className="absolute bottom-[32%] right-[20%] w-3 h-3 bg-[#72FFAE]/15 rounded-full blur-[3px] animate-float-slow pointer-events-none"
            style={{ zIndex: 2 }}
          />
          {/* Translucent organic blur */}
          <div 
            className="absolute top-[35%] left-[28%] w-[320px] h-[320px] bg-white/5 rounded-full blur-[80px] pointer-events-none"
            style={{ zIndex: 2 }}
          />

          {/* Subtle white overlays for readability */}
          <div 
            className="absolute inset-0 pointer-events-none"
            style={{
              zIndex: 1,
              background: 'linear-gradient(180deg, rgba(247,250,248,0.15) 0%, rgba(247,250,248,0.4) 65%, #F7FAF8 100%)',
            }}
          />
          <div 
            className="absolute inset-0 pointer-events-none"
            style={{
              zIndex: 1,
              backgroundColor: 'rgba(255, 255, 255, 0.18)',
            }}
          />
        </div>

        {/* Hero Content (Floating UI with mouse parallax) */}
        {/* Centered vertically and pushed down to clear the nav bar */}
        <motion.div
          style={{ x: mousePos.x, y: mousePos.y + 15, zIndex: 10 }}
          className="relative flex flex-col items-center text-center max-w-4xl px-6 md:px-12 mt-28"
        >
          {/* Announcement Badge */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.02, boxShadow: '0 0 15px rgba(20,216,111,0.15)' }}
            transition={{ duration: 0.6, delay: 0.1, ease: easeTransition }}
            className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/45 backdrop-blur-[12px] border border-white/35 rounded-full text-xs font-semibold text-[#0D1117] shadow-[0_2px_12px_rgba(0,0,0,0.02)] mb-4 select-none cursor-pointer transition-shadow duration-300"
          >
            <span className="relative flex h-2 w-2">
              {/* Softer pulse animation: 2.5s duration */}
              <span className="animate-[ping_2.5s_cubic-bezier(0.16,1,0.3,1)_infinite] absolute inline-flex h-full w-full rounded-full bg-[#14D86F] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#14D86F]"></span>
            </span>
            <span className="tracking-wide text-[10px] md:text-xs uppercase font-satoshi">
              Autonomous Agent Sentinel v5.0 is Live
            </span>
          </motion.div>

          {/* Heading */}
          {/* Font weight around 700, tighter margins & spacing */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease: easeTransition }}
            className="font-satoshi font-bold text-[54px] md:text-[90px] text-[#0D1117] tracking-[-0.03em] leading-[0.92] uppercase mb-2"
          >
            AI Agents
          </motion.h1>

          {/* Elegant serif subtitle */}
          {/* Soft green, size increased 10% */}
          <motion.h2
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3, ease: easeTransition }}
            className="font-playfair italic text-[36px] md:text-[56px] lg:text-[62px] text-[#18C467] font-medium tracking-tight mb-3"
          >
            That Think. Learn. Build.
          </motion.h2>

          {/* Description */}
          {/* Max width 620px, line-height 1.65, color: rgba(25,30,35,0.82) */}
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4, ease: easeTransition }}
            className="text-base md:text-lg mt-4 leading-[1.65] max-w-[620px] font-normal"
            style={{ color: 'rgba(25, 30, 35, 0.82)' }}
          >
            Safeguard your entire financial ecosystem with self-improving cognitive agents. Detect cross-channel laundering, suspect mule accounts, and structural splitting in milliseconds at absolute banking scale.
          </motion.p>

          {/* Buttons / CTAs */}
          <motion.div
            className="flex flex-col sm:flex-row gap-4 mt-6 w-full sm:w-auto px-4 justify-center"
          >
            {/* Primary CTA */}
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={handleLaunch}
              whileHover={{ 
                y: -2, 
                boxShadow: "0 8px 30px rgba(20,216,111,0.4)"
              }}
              whileTap={{ scale: 0.97 }}
              transition={{ duration: 0.6, delay: 0.5, ease: easeTransition }}
              className="px-8 py-4 bg-[#14D86F] hover:bg-[#11ca66] text-white font-bold rounded-full shadow-[0_4px_20px_rgba(20,216,111,0.22)] cursor-pointer text-base tracking-wide flex items-center justify-center gap-2 group btn-glossy-sweep"
              onMouseEnter={() => setIsHoveringBtn(true)}
              onMouseLeave={() => setIsHoveringBtn(false)}
            >
              Launch Workstation
              <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
            </motion.button>

            {/* Secondary CTA */}
            {/* Frosted Glass: background: rgba(255,255,255,.35), backdrop blur, white translucent border */}
            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={scrollToFeatures}
              whileHover={{ 
                y: -2, 
                backgroundColor: "rgba(255,255,255,0.50)",
                borderColor: "rgba(255,255,255,0.55)"
              }}
              whileTap={{ scale: 0.97 }}
              transition={{ duration: 0.6, delay: 0.58, ease: easeTransition }}
              className="px-8 py-4 text-[#0D1117] font-bold rounded-full shadow-sm cursor-pointer text-base tracking-wide flex items-center justify-center"
              style={{
                background: 'rgba(255, 255, 255, 0.35)',
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                border: '1px solid rgba(255, 255, 255, 0.45)',
              }}
              onMouseEnter={() => setIsHoveringBtn(true)}
              onMouseLeave={() => setIsHoveringBtn(false)}
            >
              Explore Features
            </motion.button>
          </motion.div>

          {/* Animated Scroll Indicator Stack */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.72, ease: easeTransition }}
            className="flex flex-col items-center mt-12 select-none"
            style={{ color: 'rgba(25, 30, 35, 0.6)' }}
          >
            <span className="text-[10px] md:text-xs uppercase tracking-widest font-bold mb-3">
              Trusted by builders worldwide
            </span>
            {/* Animated mouse scroll container */}
            <div className="w-5 h-8 border-2 border-current rounded-full flex justify-center pt-1.5 opacity-40">
              <motion.div
                animate={{ y: [0, 6, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                className="w-1.5 h-1.5 bg-current rounded-full"
              />
            </div>
            {/* Bouncing glowing arrow below */}
            <motion.svg
              animate={{ y: [0, 4, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
              className="w-4 h-4 text-current mt-2 opacity-40"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </motion.svg>
          </motion.div>
        </motion.div>
      </section>

      {/* ────────────────────────────────────────────────────────
         PROBLEM VS SOLUTION
         ──────────────────────────────────────────────────────── */}
      <section ref={problemRef} className="py-24 px-6 md:px-12 bg-[#F7FAF8]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-satoshi font-bold text-3xl md:text-5xl text-[#0D1117] tracking-tight uppercase mb-4">
              The Security Challenge
            </h2>
            <p className="text-sm md:text-base text-[#5E6C76] font-semibold max-w-xl mx-auto uppercase tracking-wider">
              Static rules fail. Autonomous networks demand real-time learning.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Card A: Problem */}
            <motion.div 
              whileHover={{ y: -4 }}
              transition={{ ease: easeTransition, duration: 0.4 }}
              className="bg-white/45 backdrop-blur-md border border-white/35 p-8 md:p-12 rounded-3xl flex flex-col gap-6 shadow-sm"
            >
              <div className="w-11 h-11 bg-red-50 border border-red-100 flex items-center justify-center rounded-2xl shadow-sm">
                <X className="text-red-500" size={20} />
              </div>
              <h3 className="font-satoshi font-bold text-xl md:text-2xl text-[#0D1117] uppercase tracking-tight">
                Traditional Monitoring
              </h3>
              <ul className="flex flex-col gap-4 text-sm font-medium text-[#5E6C76]">
                <li className="flex items-center gap-3">
                  <X size={16} className="text-red-500 shrink-0" /> Separated channels mean UPI & Cards never sync.
                </li>
                <li className="flex items-center gap-3">
                  <X size={16} className="text-red-500 shrink-0" /> Dynamic transaction chains go completely unnoticed.
                </li>
                <li className="flex items-center gap-3">
                  <X size={16} className="text-red-500 shrink-0" /> Manual regulatory compliance takes days instead of seconds.
                </li>
              </ul>
            </motion.div>

            {/* Card B: Solution */}
            <motion.div 
              whileHover={{ y: -4 }}
              transition={{ ease: easeTransition, duration: 0.4 }}
              className="bg-white/70 backdrop-blur-md border border-[#14D86F]/25 p-8 md:p-12 rounded-3xl flex flex-col gap-6 shadow-[0_12px_40px_rgba(20,216,111,0.05)] relative overflow-hidden"
            >
              {/* Soft green glow */}
              <div className="absolute top-0 right-0 w-24 h-24 bg-[#14D86F]/10 rounded-full blur-2xl pointer-events-none" />
              
              <div className="w-11 h-11 bg-[#14D86F]/10 border border-[#14D86F]/20 flex items-center justify-center rounded-2xl shadow-sm">
                <Check className="text-[#14D86F]" size={20} />
              </div>
              <h3 className="font-satoshi font-bold text-xl md:text-2xl text-[#0D1117] uppercase tracking-tight">
                Aegis Sentinel Agent Platform
              </h3>
              <ul className="flex flex-col gap-4 text-sm font-medium text-[#0D1117]/80">
                <li className="flex items-center gap-3">
                  <Check size={16} className="text-[#14D86F] shrink-0" /> Fully unified cross-channel early warning indicators.
                </li>
                <li className="flex items-center gap-3">
                  <Check size={16} className="text-[#14D86F] shrink-0" /> Real-time PageRank-powered graph database and memory logs.
                </li>
                <li className="flex items-center gap-3">
                  <Check size={16} className="text-[#14D86F] shrink-0" /> Automated regulatory CRILC filing and FIU-IND queue tools.
                </li>
              </ul>
            </motion.div>
          </div>
        </div>
      </section>


      {/* ────────────────────────────────────────────────────────
         FEATURE GRID
         ──────────────────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6 md:px-12 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-satoshi font-bold text-3xl md:text-5xl text-[#0D1117] tracking-tight uppercase mb-4">
              Built For Critical Scale
            </h2>
            <p className="text-sm md:text-base text-[#5E6C76] font-semibold max-w-xl mx-auto uppercase tracking-wider">
              Robust capabilities engineered for modern banking architectures.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Cross-Channel Ingestion',
                desc: 'Real-time telemetry pipelines capture UPI, IMPS, RTGS, and card payments in a single unified cognitive thread.',
                icon: Cpu
              },
              {
                title: 'Mule Suspicion Engine',
                desc: 'Early warning indicators detect dormancy breaks, high velocity spikes, and high-frequency in-and-out hops.',
                icon: Shield
              },
              {
                title: 'Graph Intelligence',
                desc: 'Visualizes money flows, loops, and transaction rings inside our custom force-directed graph canvas.',
                icon: Fingerprint
              }
            ].map((feat, i) => (
              <motion.div
                key={i}
                whileHover={{ y: -4 }}
                transition={{ ease: easeTransition, duration: 0.3 }}
                className="group bg-[#F7FAF8]/50 backdrop-blur-sm border border-gray-100 p-8 rounded-3xl shadow-sm hover:shadow-md transition-shadow duration-300 flex flex-col gap-6"
              >
                <div className="w-12 h-12 bg-[#B8FFD7]/30 border border-[#72FFAE]/30 flex items-center justify-center rounded-2xl text-[#14D86F] shadow-[0_4px_12px_rgba(20,216,111,0.05)] transition-colors duration-300 group-hover:bg-[#14D86F] group-hover:text-white">
                  <feat.icon size={20} />
                </div>
                <h3 className="font-satoshi font-bold text-lg text-[#0D1117] uppercase tracking-tight">
                  {feat.title}
                </h3>
                <p className="text-sm text-[#5E6C76] leading-relaxed font-medium">
                  {feat.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>


      {/* ────────────────────────────────────────────────────────
         HOW IT WORKS
         ──────────────────────────────────────────────────────── */}
      <section id="how-it-works" className="py-24 px-6 md:px-12 bg-[#F7FAF8]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="font-satoshi font-bold text-3xl md:text-5xl text-[#0D1117] tracking-tight uppercase mb-4">
              How It Works
            </h2>
            <p className="text-sm md:text-base text-[#5E6C76] font-semibold max-w-xl mx-auto uppercase tracking-wider">
              Three modular steps to total compliance and security.
            </p>
          </div>

          <div className="relative">
            {/* Connection Line */}
            <div className="absolute top-12 left-0 right-0 h-0.5 bg-gray-200/60 hidden md:block z-0" />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative z-10">
              {[
                {
                  step: '01',
                  title: 'Data Ingestion',
                  desc: 'We pipe transaction messages from COBOL simulator cores via high-performance resilient brokers.'
                },
                {
                  step: '02',
                  title: 'Real-time Scans',
                  desc: 'ML classification and complex early warning loops identify anomalies in under 5 milliseconds.'
                },
                {
                  step: '03',
                  title: 'Actionable Alerts',
                  desc: 'Our OS produces full intelligence records, government filing logs, and compliance forms.'
                }
              ].map((step, i) => (
                <div key={i} className="flex flex-col items-center text-center gap-4">
                  <div className="w-20 h-20 rounded-full bg-white border border-[#14D86F]/30 flex items-center justify-center font-satoshi font-bold text-xl text-[#0D1117] shadow-sm relative">
                    {/* Ring glow */}
                    <div className="absolute inset-0 rounded-full border-4 border-[#14D86F]/10 animate-ping opacity-25" />
                    {step.step}
                  </div>
                  <h3 className="font-satoshi font-bold text-lg text-[#0D1117] uppercase tracking-tight mt-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-[#5E6C76] leading-relaxed max-w-xs font-medium">
                    {step.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>


      {/* ────────────────────────────────────────────────────────
         USE CASE PERSONAS
         ──────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 md:px-12 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-satoshi font-bold text-3xl md:text-5xl text-[#0D1117] tracking-tight uppercase mb-4">
              Engineered For Every Role
            </h2>
            <p className="text-sm md:text-base text-[#5E6C76] font-semibold max-w-xl mx-auto uppercase tracking-wider">
              Workflows tailored for security teams, compliance officers, and executives.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Persona 1: Compliance */}
            <motion.div 
              whileHover={{ y: -4 }}
              transition={{ ease: easeTransition, duration: 0.3 }}
              className="bg-[#F7FAF8]/60 border border-gray-100 p-8 rounded-3xl flex flex-col gap-6 shadow-sm relative overflow-hidden"
            >
              <div className="px-3 py-1 bg-white border border-gray-200 rounded-full font-semibold text-[10px] uppercase tracking-wide self-start shadow-sm text-[#5E6C76]">
                Compliance Lead
              </div>
              <h3 className="font-satoshi font-bold text-xl text-[#0D1117] uppercase tracking-tight">
                Automated STR Reporting
              </h3>
              <p className="text-sm text-[#5E6C76] font-medium leading-relaxed">
                Ensure regulatory alignment with automatic FIU-IND report generation and structured CRILC audit trails in seconds.
              </p>
            </motion.div>

            {/* Persona 2: Risk Investigator */}
            <motion.div 
              whileHover={{ y: -4 }}
              transition={{ ease: easeTransition, duration: 0.3 }}
              className="bg-[#F7FAF8]/80 border border-[#14D86F]/20 p-8 rounded-3xl flex flex-col gap-6 shadow-md relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-16 h-16 bg-[#14D86F]/5 rounded-full blur-xl pointer-events-none" />
              <div className="px-3 py-1 bg-[#14D86F]/10 border border-[#14D86F]/20 rounded-full font-bold text-[10px] uppercase tracking-wide self-start shadow-sm text-[#14D86F]">
                Risk Investigator
              </div>
              <h3 className="font-satoshi font-bold text-xl text-[#0D1117] uppercase tracking-tight">
                Dynamic Visual Explorer
              </h3>
              <p className="text-sm text-[#5E6C76] font-medium leading-relaxed">
                Track flow paths, discover hidden transaction groups, and execute precise transaction node investigations.
              </p>
            </motion.div>

            {/* Persona 3: Executive */}
            <motion.div 
              whileHover={{ y: -4 }}
              transition={{ ease: easeTransition, duration: 0.3 }}
              className="bg-[#F7FAF8]/60 border border-gray-100 p-8 rounded-3xl flex flex-col gap-6 shadow-sm relative overflow-hidden"
            >
              <div className="px-3 py-1 bg-white border border-gray-200 rounded-full font-semibold text-[10px] uppercase tracking-wide self-start shadow-sm text-[#5E6C76]">
                Security Executive
              </div>
              <h3 className="font-satoshi font-bold text-xl text-[#0D1117] uppercase tracking-tight">
                System Telemetry
              </h3>
              <p className="text-sm text-[#5E6C76] font-medium leading-relaxed">
                Acquire systemic statistics, high-priority counts, and live connection telemetry from internal simulator threads.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ────────────────────────────────────────────────────────
         FINAL CTA
         ──────────────────────────────────────────────────────── */}
      <section className="py-32 px-6 md:px-12 bg-white relative overflow-hidden">
        {/* Ambient green glow background spotlights */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-[#14D86F]/5 rounded-full blur-3xl pointer-events-none z-0" />
        
        <div className="max-w-4xl mx-auto flex flex-col items-center gap-6 relative z-10 text-center">
          <h2 className="font-satoshi font-bold text-4xl md:text-6xl text-[#0D1117] tracking-tight uppercase max-w-2xl leading-[1.05]">
            Secure your financial infrastructure.
          </h2>
          <p className="text-base md:text-lg text-[#5E6C76] max-w-md mb-4 font-medium">
            Protect your institution. Deploy real-time fraud operating systems in minutes.
          </p>
          
          <motion.button 
            onClick={handleLaunch}
            whileHover={{ 
              y: -4, 
              boxShadow: "0 0 25px rgba(20,216,111,0.6)",
              backgroundColor: "#11ca66"
            }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: "spring", stiffness: 400, damping: 15 }}
            className="px-8 py-4 bg-[#14D86F] text-white font-bold rounded-full shadow-[0_0_15px_rgba(20,216,111,0.25)] cursor-pointer text-base tracking-wide flex items-center justify-center gap-2 group"
          >
            Launch Operating Workstation
            <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
          </motion.button>
        </div>
      </section>


      {/* ────────────────────────────────────────────────────────
         FOOTER
         ──────────────────────────────────────────────────────── */}
      <footer className="bg-[#0D1117] text-white py-16 px-6 md:px-12 border-t border-gray-800">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12">
          {/* Col 1 */}
          <div className="flex flex-col gap-4">
            <span className="font-satoshi font-bold text-lg uppercase tracking-tight text-[#14D86F]">
              AEGIS SENTINEL
            </span>
            <p className="text-xs text-gray-400 leading-relaxed max-w-xs">
              Autonomous cognitive guard and early-warning fraud operating workstation built for high-performance scale.
            </p>
            {/* Social Icons */}
            <div className="flex gap-2.5 mt-2">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center transition-all duration-200 hover:bg-[#14D86F] hover:text-white"
                aria-label="GitHub"
              >
                <svg className="w-3.5 h-3.5 fill-current text-white" viewBox="0 0 24 24">
                  <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.07 2.91.83.1-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" />
                </svg>
              </a>
              <a
                href="https://discord.com"
                target="_blank"
                rel="noopener noreferrer"
                className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center transition-all duration-200 hover:bg-[#14D86F] hover:text-white"
                aria-label="Discord"
              >
                <svg className="w-3.5 h-3.5 fill-current text-white" viewBox="0 0 24 24">
                  <path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.094 13.094 0 01-1.873-.894.077.077 0 01-.008-.128c.126-.093.252-.19.372-.287a.075.075 0 01.077-.011c3.92 1.793 8.18 1.793 12.061 0a.073.073 0 01.078.009c.12.099.246.195.373.289a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.894.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.156 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.156-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.156 2.418z" />
                </svg>
              </a>
              <a
                href="#"
                className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center transition-all duration-200 hover:bg-[#14D86F] hover:text-white"
                aria-label="Website"
              >
                <Globe size={14} />
              </a>
            </div>
          </div>

          {/* Col 2 */}
          <div className="flex flex-col gap-3 text-sm">
            <h4 className="font-satoshi font-bold text-white uppercase text-xs tracking-wider">Product</h4>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Security Workstation</a>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Compliance Analytics</a>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">API Integrations</a>
          </div>

          {/* Col 3 */}
          <div className="flex flex-col gap-3 text-sm">
            <h4 className="font-satoshi font-bold text-white uppercase text-xs tracking-wider">Resources</h4>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Developer Docs</a>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">System Status</a>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Incident Response</a>
          </div>

          {/* Col 4 */}
          <div className="flex flex-col gap-3 text-sm">
            <h4 className="font-satoshi font-bold text-white uppercase text-xs tracking-wider">Legal</h4>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Privacy Statement</a>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Terms of Work</a>
            <a href="#" className="text-xs text-gray-400 hover:text-white transition-colors duration-200">Audit Certifications</a>
          </div>
        </div>

        <div className="max-w-6xl mx-auto border-t border-gray-800 mt-12 pt-6 flex flex-col md:flex-row justify-between items-center text-xs text-gray-400 gap-4">
          <span>&copy; {new Date().getFullYear()} Aegis Sentinel platform. All Rights Reserved.</span>
          <span className="font-mono text-[10px] text-gray-500">VER V5.0-ECO</span>
        </div>
      </footer>
    </div>
  );
}
