import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Briefcase, Search, FileText, Zap } from 'lucide-react';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: 'easeOut' },
  }),
};

const features = [
  {
    icon: Search,
    title: 'Smart Job Search',
    description:
      'Aggregate listings from top platforms and filter by role, location, and salary — all in one unified feed.',
  },
  {
    icon: FileText,
    title: 'AI Resume Tailoring',
    description:
      'Instantly reshape your resume and cover letter to match every job description with one click.',
  },
  {
    icon: Zap,
    title: 'Automated Apply',
    description:
      'Submit applications across portals automatically while you focus on interview prep.',
  },
];

const steps = [
  { num: '01', title: 'Search', desc: 'Find roles that match your profile' },
  { num: '02', title: 'Compose', desc: 'AI tailors your resume in seconds' },
  { num: '03', title: 'Apply', desc: 'Submit with a single click' },
];

const stats = [
  { value: '10x', label: 'Faster applications' },
  { value: '60s', label: 'Average compose time' },
  { value: '100%', label: 'Profile customization' },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navbar */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-black/80 backdrop-blur-md border-b border-[#222222]">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 h-14">
          <div className="flex items-center gap-2">
            <Briefcase className="w-5 h-5 text-white" />
            <span className="text-base font-semibold tracking-tight">Workify</span>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="text-sm text-[#888888] hover:text-white transition-colors"
          >
            Sign in
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="min-h-screen flex flex-col items-center justify-center text-center px-6 pt-14">
        <motion.h1
          className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1]"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0}
        >
          Apply smarter.
          <br />
          Not harder.
        </motion.h1>
        <motion.p
          className="mt-6 text-lg text-[#888888] max-w-xl leading-relaxed"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={1}
        >
          AI-powered job applications that adapt to every listing. Your profile,
          tailored resumes, and automated submissions — all in one place.
        </motion.p>
        <motion.button
          onClick={() => navigate('/login')}
          className="mt-10 bg-white text-black rounded-full px-8 py-3 text-sm font-medium hover:bg-neutral-200 transition-colors"
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={2}
        >
          Get started — it's free
        </motion.button>
      </section>

      {/* Feature Grid */}
      <section className="max-w-6xl mx-auto px-6 py-24">
        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
        >
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              className="glass-card p-6"
              variants={fadeUp}
              custom={i}
            >
              <f.icon className="w-5 h-5 text-[#888888] mb-4" />
              <h3 className="text-white font-medium mb-1">{f.title}</h3>
              <p className="text-sm text-[#888888] leading-relaxed">
                {f.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* How It Works */}
      <section className="max-w-4xl mx-auto px-6 py-24">
        <motion.h2
          className="text-center text-2xl md:text-3xl font-bold tracking-tight mb-16"
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          How it works
        </motion.h2>
        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-8 relative"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
        >
          {/* connecting line (desktop) */}
          <div className="hidden md:block absolute top-5 left-[16.67%] right-[16.67%] h-px bg-[#222222]" />

          {steps.map((s, i) => (
            <motion.div
              key={s.num}
              className="flex flex-col items-center text-center"
              variants={fadeUp}
              custom={i}
            >
              <div className="relative z-10 w-10 h-10 rounded-full border border-[#222222] bg-black flex items-center justify-center text-xs text-[#888888] font-mono mb-4">
                {s.num}
              </div>
              <h3 className="text-white font-medium mb-1">{s.title}</h3>
              <p className="text-sm text-[#888888]">{s.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Stats */}
      <section className="max-w-4xl mx-auto px-6 py-24">
        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
        >
          {stats.map((s, i) => (
            <motion.div key={s.label} variants={fadeUp} custom={i}>
              <span className="text-4xl md:text-5xl font-bold tracking-tight">
                {s.value}
              </span>
              <p className="mt-2 text-sm text-[#888888]">{s.label}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* CTA */}
      <section className="py-24 text-center px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          <motion.h2
            className="text-2xl md:text-3xl font-bold tracking-tight mb-6"
            variants={fadeUp}
            custom={0}
          >
            Ready to apply smarter?
          </motion.h2>
          <motion.button
            onClick={() => navigate('/login')}
            className="bg-white text-black rounded-full px-8 py-3 text-sm font-medium hover:bg-neutral-200 transition-colors"
            variants={fadeUp}
            custom={1}
          >
            Get started — it's free
          </motion.button>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#222222] py-8">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-[#888888]" />
            <span className="text-sm font-medium text-[#888888]">Workify</span>
          </div>
          <span className="text-xs text-[#888888]">Built for job seekers</span>
        </div>
      </footer>
    </div>
  );
}
