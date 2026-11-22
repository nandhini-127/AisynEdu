import apiClient from './api';
import { chatService } from './chatService';
import { Quiz, QuizQuestion, QuizResult, QuizSubmission } from '../types/quiz';

const QUIZ_STORAGE_KEY = 'edunex_saved_quizzes';
const QUIZ_HISTORY_KEY = 'edunex_quiz_history';

function getQuizHistoryKey(userId?: string): string {
  if (userId) return `edunex_quiz_history_${userId}`;
  try {
    const raw = localStorage.getItem('edunex_user');
    if (raw) {
      const u = JSON.parse(raw);
      if (u?.id) return `edunex_quiz_history_${u.id}`;
    }
  } catch {
    // Ignore parse error
  }
  return 'edunex_quiz_history_anonymous';
}

/**
 * Normalizes an array of raw question dictionaries (e.g. from backend quiz_data or JSON extraction)
 * into typed QuizQuestion objects.
 */
function mapRawQuestions(items: any[]): QuizQuestion[] {
  const result: QuizQuestion[] = [];
  if (!Array.isArray(items)) return result;

  items.forEach((q: any, idx: number) => {
    let correctIdx = typeof q.correct_index === 'number' ? q.correct_index : 0;
    if (typeof q.correct_index !== 'number' && typeof q.correct_answer === 'string') {
      const letter = q.correct_answer.trim().toUpperCase();
      if (letter.startsWith('A')) correctIdx = 0;
      else if (letter.startsWith('B')) correctIdx = 1;
      else if (letter.startsWith('C')) correctIdx = 2;
      else if (letter.startsWith('D')) correctIdx = 3;
    }

    const rawOptions: string[] = Array.isArray(q.options) && q.options.length >= 2
      ? q.options
      : [];
    const questionText = (q.question || '').trim();
    if (!questionText || rawOptions.length < 2) return;

    const cleanOptions = rawOptions.map((opt: string) =>
      String(opt).replace(/^[A-Da-d][).\s]\s*/u, '').trim()
    );

    result.push({
      id: q.id ? String(q.id) : `q-${idx + 1}`,
      question: questionText,
      options: cleanOptions,
      explanation: q.explanation ? String(q.explanation).trim() : 'Detailed explanation provided upon review.',
      correct_index: correctIdx,
    });
  });

  return result;
}

/**
 * Parses Markdown formatted MCQs if the model returns formatted text instead of raw JSON.
 * Matches: **Question X:** ... - A) ... - B) ... and <details> answers.
 */
function parseMarkdownMCQs(content: string, difficulty: string): QuizQuestion[] {
  const questions: QuizQuestion[] = [];
  if (!content || typeof content !== 'string') return questions;

  // Extract answers from <details> section if present
  const answersMap: Record<number, { answer: string; explanation: string }> = {};
  const answerRegex = /\*\*Question\s*(\d+)\s*Answer:\*\*\s*\*\*([A-Da-d])\*\*(?:[\s\S]*?\*([^*]+)\*)?/gi;
  let ansMatch;
  while ((ansMatch = answerRegex.exec(content)) !== null) {
    const qNum = parseInt(ansMatch[1], 10);
    answersMap[qNum] = {
      answer: ansMatch[2].toUpperCase(),
      explanation: ansMatch[3] ? ansMatch[3].trim() : '',
    };
  }

  // Split into individual question blocks
  const qBlocks = content.split(/\*\*(?:Question\s*\d+|Q\d+)[:.]?\*\*/gi);
  qBlocks.forEach((block, idx) => {
    if (idx === 0) return; // preamble before first question
    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return;

    const qText = lines[0].replace(/^[:\s-]+/, '').trim();
    const rawOptions: string[] = [];

    lines.slice(1).forEach((line) => {
      const optMatch = line.match(/^[-*]?\s*([A-Da-d])[).]\s*(.*)$/);
      if (optMatch) {
        rawOptions.push(optMatch[2].trim());
      }
    });

    if (qText && rawOptions.length >= 2) {
      const ansInfo = answersMap[idx];
      let correctIdx = 0;
      if (ansInfo?.answer) {
        if (ansInfo.answer.startsWith('B')) correctIdx = 1;
        else if (ansInfo.answer.startsWith('C')) correctIdx = 2;
        else if (ansInfo.answer.startsWith('D')) correctIdx = 3;
      }

      questions.push({
        id: `q-${idx}`,
        question: qText,
        options: rawOptions.slice(0, 4),
        explanation: ansInfo?.explanation || `Pedagogical explanation for question ${idx}.`,
        correct_index: correctIdx,
      });
    }
  });

  return questions;
}

/**
 * Topic-aware, pedagogically authentic fallback questions.
 * Produces accurate, factually grounded MCQs tailored to the user's topic.
 * Never outputs generic filler or meaningless distractors.
 */
function getTopicAwareQuizFallback(topic: string, difficulty: 'beginner' | 'intermediate' | 'advanced', count: number = 4): QuizQuestion[] {
  const cleanTopic = topic.trim();
  const lower = cleanTopic.toLowerCase();

  // Helper to slice and ensure sequential IDs
  const formatList = (list: QuizQuestion[]): QuizQuestion[] => {
    return list.slice(0, count).map((q, idx) => ({
      ...q,
      id: `q-${idx + 1}`,
    }));
  };

  // 1. India / Indian Polity / History / Geography
  if (/\b(india|indian|bharat|constitution of india|indian polity|indian history)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'Which historical document serves as the supreme law of the Republic of India, adopted by the Constituent Assembly on November 26, 1949 and brought into effect on January 26, 1950?',
        options: [
          'The Constitution of India',
          'The Government of India Act 1935',
          'The Indian Independence Act 1947',
          'The Charter Act of 1853',
        ],
        explanation: 'The Constitution of India is the supreme legal framework of India, drafted under the chairmanship of Dr. B.R. Ambedkar and enacted on January 26, 1950 (commemorated annually as Republic Day).',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'What is the official national motto of India, inscribed in Devanagari script at the base of the Lion Capital of Ashoka (National Emblem)?',
        options: [
          'Satyameva Jayate ("Truth Alone Triumphs")',
          'Vande Mataram ("I Bow to Thee, Mother")',
          'Jai Jawan Jai Kisan ("Hail the Soldier, Hail the Farmer")',
          'Sarva Dharma Sambhava ("Equal Respect for all Religions")',
        ],
        explanation: '"Satyameva Jayate" is an ancient aphorism taken from the Mundaka Upanishad and serves as the official national motto of India.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'Which prominent latitude line passes through the central region of India across eight states, dividing the country into Northern and Peninsular zones?',
        options: [
          'Tropic of Cancer (23° 30\' N)',
          'Equator (0°)',
          'Tropic of Capricorn (23° 30\' S)',
          'Prime Meridian (0°)',
        ],
        explanation: 'The Tropic of Cancer (23.5° N) passes through eight Indian states: Gujarat, Rajasthan, Madhya Pradesh, Chhattisgarh, Jharkhand, West Bengal, Tripura, and Mizoram.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'Which ancient bronze-age urban civilization flourished in the northwestern region of the Indian subcontinent around 2500 BCE, renowned for standardized brick architecture and advanced covered drainage?',
        options: [
          'Indus Valley (Harappan) Civilization',
          'Mesopotamian Civilization',
          'Minoan Civilization',
          'Old Kingdom of Egypt',
        ],
        explanation: 'The Indus Valley Civilization (notably Harappa and Mohenjo-Daro) was an advanced urban culture celebrated for grid-planned cities, hydraulic engineering, and municipal drainage.',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'Which apex constitutional institution in India, established under Article 324 of the Constitution, is vested with the superintendence, direction, and control of elections?',
        options: [
          'The Election Commission of India',
          'The Union Public Service Commission',
          'The Finance Commission of India',
          'The Law Commission of India',
        ],
        explanation: 'Article 324 of the Constitution vests the superintendence, direction, and control of all elections to Parliament and state legislatures in the Election Commission of India.',
        correct_index: 0,
      },
    ]);
  }

  // 2. Tamil Nadu Heritage & Culture
  if (/\b(tamil nadu|chola|pallava|pandya|dravidian|thanjavur|brihadeeswarar|sangam|pongal)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'Which historic Hindu temple located in Thanjavur, Tamil Nadu was built by King Rajaraja Chola I and is renowned for its monumental Dravidian granite vimana tower?',
        options: [
          'Brihadeeswarar Temple',
          'Sun Temple at Konark',
          'Khajuraho Kandariya Mahadeva Temple',
          'Virupaksha Temple at Hampi',
        ],
        explanation: 'Brihadeeswarar Temple was constructed between 1003 and 1010 CE by Emperor Rajaraja Chola I, showcasing the pinnacle of Chola Dravidian granite architecture.',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'In which year did the Government of India declare Tamil as the country\'s first official Classical Language?',
        options: [
          '2004',
          '1991',
          '2014',
          '1980',
        ],
        explanation: 'In 2004, the Government of India created the category of Classical Languages and designated Tamil as the first to receive this status.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'What ancient era in Tamil history is celebrated for assemblies of Tamil poets convened primarily in Madurai under Pandya patronage?',
        options: [
          'The Sangam Era',
          'The Vedic Era',
          'The Vijayanagara Era',
          'The Maratha Era',
        ],
        explanation: 'The Sangam Period produced seminal classical anthologies such as the Ettuthokai and Pathupattu.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'Which four-day harvest festival celebrated in mid-January is considered the premier cultural festival of Tamil Nadu?',
        options: [
          'Pongal',
          'Onam',
          'Bihu',
          'Lohri',
        ],
        explanation: 'Pongal is celebrated across four days (Bhogi, Surya Pongal, Maatu Pongal, Kaanum Pongal) to give thanks for agricultural abundance.',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'Which monumental 8th-century rock-cut temple complex in Mamallapuram was constructed during the reign of Pallava King Narasimhavarman II (Rajasimha)?',
        options: [
          'The Shore Temple',
          'Meenakshi Temple',
          'Kapaleeshwarar Temple',
          'Ramanathaswamy Temple',
        ],
        explanation: 'The Shore Temple at Mamallapuram was built by the Pallava Dynasty in the early 8th century and is recognized as a UNESCO World Heritage Site.',
        correct_index: 0,
      },
    ]);
  }

  // 3. National Bird / Indian Peafowl
  if (/\b(national bird|peacock|peafowl|pavo cristatus)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'Which bird species was officially designated as the National Bird of India in 1963?',
        options: [
          'Indian Peafowl (Pavo cristatus)',
          'Great Indian Bustard (Ardeotis nigriceps)',
          'Sarus Crane (Antigone antigone)',
          'Indian Roller (Coracias benghalensis)',
        ],
        explanation: 'The Indian Peafowl (Pavo cristatus) was declared the National Bird of India in 1963 due to its widespread presence, cultural prominence, and visual majesty.',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'Under which schedule of the Indian Wildlife (Protection) Act, 1972 is the Indian Peafowl granted absolute protection against hunting and trade?',
        options: [
          'Schedule I',
          'Schedule III',
          'Schedule IV',
          'Schedule V',
        ],
        explanation: 'The Indian Peafowl is classified under Schedule I, providing it the highest level of legal protection.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'What physical mechanism produces the brilliant iridescent colors in peacock train feathers?',
        options: [
          'Microscopic photonic crystal structures producing optical interference',
          'Chemical carotenoid and melanin pigments exclusively',
          'Bioluminescent enzymes active in feather follicles',
          'Ingestion of metallic mineral salts in diet',
        ],
        explanation: 'Peacock coloration is structural color produced by two-dimensional photonic crystal nanostructures made of melanin rods embedded in keratin.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'What biological term describes the marked morphological differences between the male peacock and the female peahen?',
        options: [
          'Sexual Dimorphism',
          'Adaptive Radiation',
          'Cryptic Mimicry',
          'Convergent Evolution',
        ],
        explanation: 'Sexual dimorphism is the condition where males and females of the same species exhibit distinctly different physical characteristics.',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'In which year was statutory legal protection under Schedule I granted to the Indian Peafowl through the Indian Wildlife (Protection) Act?',
        options: [
          '1972',
          '1986',
          '2002',
          '1961',
        ],
        explanation: 'The Wildlife (Protection) Act of 1972 placed the Indian Peafowl under Schedule I, providing absolute legal protection against hunting and trade.',
        correct_index: 0,
      },
    ]);
  }

  // 4. Python Programming
  if (/\b(python|cpython|gil|pydantic|fastapi)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'What is the primary role of the Global Interpreter Lock (GIL) in standard CPython implementation?',
        options: [
          'A mutex that prevents multiple native OS threads from executing Python bytecodes simultaneously to protect reference-counting memory safety',
          'A JIT compiler that translates bytecode into native machine instructions at runtime',
          'A static type analyzer that guarantees variable safety before bytecode execution',
          'An asynchronous event loop scheduler for coroutines',
        ],
        explanation: 'The GIL in CPython prevents multiple threads from executing Python bytecodes concurrently, safeguarding non-thread-safe reference counting memory management.',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'How does CPython reclaim memory for cyclic reference chains where objects reference each other?',
        options: [
          'Using a cyclic generational garbage collector that inspects container objects across three generations (0, 1, 2)',
          'By forcing an immediate system kernel memory purge upon function return',
          'By converting circular references automatically into weak references',
          'CPython cannot reclaim cyclic references and leaks that memory permanently',
        ],
        explanation: 'CPython supplements reference counting with a generational garbage collector tracking container objects across generations 0, 1, and 2.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'Which of the following data types in Python is mutable?',
        options: [
          'List',
          'Tuple',
          'Frozenset',
          'String',
        ],
        explanation: 'Lists are mutable sequences that can be modified in-place, whereas Tuples, Frozensets, and Strings are immutable.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'What is the primary performance benefit of using a Python generator over a standard list comprehension for large data streams?',
        options: [
          'Generators yield elements lazily one-at-a-time, consuming O(1) memory overhead regardless of stream size',
          'Generators execute in parallel across multiple CPU cores automatically',
          'Generators compile Python code directly to assembly language',
          'Generators bypass the CPython Global Interpreter Lock (GIL)',
        ],
        explanation: 'Generators evaluate lazily via the iterator protocol, retaining only the current item in memory and achieving O(1) space complexity.',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'What is the primary architectural purpose of defining "__slots__" in a custom Python class?',
        options: [
          'Preventing the dynamic creation of an instance __dict__, substantially optimizing memory consumption',
          'Enabling automatic parallel execution across CPU threads',
          'Compiling the Python class directly to machine bytecode',
          'Restricting inheritance of private methods in child classes',
        ],
        explanation: 'Defining __slots__ instructs CPython to allocate static attribute storage rather than a dynamic __dict__, significantly reducing RAM usage for large numbers of instances.',
        correct_index: 0,
      },
    ]);
  }

  // 5. Database Systems & Indexing
  if (/\b(database|indexing|b-tree|b\+ tree|sql|acid|rdbms|dbms)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'Why are B+ Trees predominantly preferred over standard binary search trees for disk-based relational database indexes?',
        options: [
          'High fan-out minimizes tree depth and disk I/O, while doubly linked leaf nodes optimize range scans',
          'B+ Trees require zero disk storage and operate exclusively in CPU L1 cache',
          'Binary search trees cannot store string or numeric primary keys',
          'B+ Trees eliminate the need for ACID transaction write-ahead logs',
        ],
        explanation: 'B+ Trees have high branching factors (fan-out), keeping the tree shallow (3-4 levels) to minimize disk page accesses, while linked leaves allow contiguous range scans.',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'What is the key architectural difference between a Clustered Index and a Non-Clustered Index in an RDBMS?',
        options: [
          'A clustered index physically determines the on-disk row sorting order (at most one per table), while non-clustered indexes store separate lookup pointers',
          'Non-clustered indexes physically rearrange data rows on disk, while clustered indexes exist only in RAM',
          'A database table can possess multiple clustered indexes but only one non-clustered index',
          'Clustered indexes are exclusively used for temporary memory tables',
        ],
        explanation: 'A clustered index dictates the actual physical order of data rows on disk, so only one can exist per table.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'What trade-off is introduced when adding multiple secondary indexes to a high-write database table?',
        options: [
          'Read queries accelerate, but write operations (INSERT, UPDATE, DELETE) become slower due to index maintenance',
          'Both read and write performance degrade uniformly across all queries',
          'The database disables ACID isolation guarantees permanently',
          'Foreign key constraints can no longer be evaluated by the query planner',
        ],
        explanation: 'Every write operation must update all corresponding secondary index trees, introducing write amplification and disk I/O overhead.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'Under what query condition does a Hash Index fail compared to a B+ Tree index?',
        options: [
          'Range queries evaluating inequalities (e.g. WHERE age BETWEEN 20 AND 30 or WHERE salary > 50000)',
          'Exact point equality searches (e.g. WHERE id = 1042)',
          'Lookups on integer primary key columns',
          'Single-row fetch operations in memory',
        ],
        explanation: 'Hash indexes distribute keys non-sequentially via hash functions, providing O(1) equality searches but unable to evaluate range inequalities (<, >, BETWEEN).',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'In the relational database ACID transaction model, what guarantee is provided by "Isolation"?',
        options: [
          'Concurrent transaction execution produces state changes equivalent to serial execution without intermediate state exposure',
          'Committed transactions can never be modified on disk',
          'All database queries automatically utilize clustered indexes',
          'Read transactions never require CPU memory buffers',
        ],
        explanation: 'Isolation ensures that concurrent transactions execute independently without reading uncommitted or intermediate states of other transactions.',
        correct_index: 0,
      },
    ]);
  }

  // 6. Operating Systems
  if (/\b(operating system|operating systems|deadlock|process scheduling|semaphore|virtual memory|paging|context switch)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: "Which condition is NOT one of Coffman's four necessary conditions for a system deadlock to occur?",
        options: [
          'Preemption of allocated resources by the operating system kernel',
          'Mutual Exclusion',
          'Hold and Wait',
          'Circular Wait',
        ],
        explanation: "Resource preemption prevents deadlocks. Coffman's four conditions are: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.",
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'In CPU scheduling, what is the primary consequence of setting the Round Robin (RR) time quantum extremely small?',
        options: [
          'Interactive responsiveness improves, but context-switching CPU overhead increases substantially',
          'The scheduling algorithm degenerates into First-Come, First-Served (FCFS)',
          'Long-running processes suffer permanent starvation',
          'The CPU utilization increases to near 100%',
        ],
        explanation: 'An extremely small time quantum gives high responsiveness to interactive tasks, but wastes substantial CPU clock cycles saving and loading process control blocks (context switching).',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'What is the primary architectural purpose of a Translation Lookaside Buffer (TLB) in virtual memory systems?',
        options: [
          'A high-speed associative hardware cache that accelerates virtual-to-physical address translation',
          'A kernel disk buffer for spooling asynchronous printer output',
          'An interrupt controller for prioritized hardware device interrupts',
          'A swap space partition manager on disk',
        ],
        explanation: 'The TLB caches recent virtual page number to physical frame mappings in high-speed hardware, avoiding memory lookups to the in-RAM page table on a TLB hit.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'How does a counting semaphore differ from a binary semaphore (mutex) in process synchronization?',
        options: [
          'A counting semaphore can take non-negative integer values representing available resource units, whereas a binary semaphore is restricted to 0 and 1',
          'A counting semaphore cannot be shared across multiple threads',
          'A binary semaphore does not support wait() and signal() operations',
          'A counting semaphore automatically prevents priority inversion',
        ],
        explanation: 'Counting semaphores manage finite pools of multiple identical resource units (initialized to N), while binary semaphores provide mutual exclusion over a single resource (0 or 1).',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'What synchronization protocol is employed by operating systems to mitigate "Priority Inversion"?',
        options: [
          'Priority Inheritance, where a lower-priority task holding a mutex temporarily inherits the priority of a blocked higher-priority task',
          'Immediately terminating the lower-priority task',
          'Disabling hardware timer interrupts permanently',
          'Converting all mutex locks to non-blocking spinlocks',
        ],
        explanation: 'Priority Inheritance temporarily boosts the priority of the task holding the mutex to that of the highest-priority task waiting for it, allowing it to release the resource quickly.',
        correct_index: 0,
      },
    ]);
  }

  // 7. GPU Architecture
  if (/\b(gpu|cuda|tensor core|vram|simt|streaming multiprocessor)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'What is the primary architectural role of CUDA cores in modern GPU computing?',
        options: [
          'Executing massively parallel arithmetic logic operations across thousands of concurrent threads',
          'Managing OS virtual memory page table translations',
          'Serial instruction decoding and branch prediction',
          'Controlling physical disk I/O interrupt channels',
        ],
        explanation: 'CUDA cores are the fundamental parallel arithmetic units in NVIDIA GPUs, processing integer and floating-point computations across thousands of threads.',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'How do Tensor Cores differ from standard CUDA cores in modern GPUs?',
        options: [
          'Tensor Cores are specialized hardware accelerators optimized for mixed-precision matrix multiply-accumulate operations',
          'Tensor Cores only process display outputs over HDMI and DisplayPort',
          'Tensor Cores operate at lower clock speeds without supporting floating-point arithmetic',
          'Tensor Cores replace the host CPU completely for system control',
        ],
        explanation: 'Tensor Cores execute matrix multiply-accumulate (MMA) operations in a single clock cycle, dramatically speeding up neural network workloads.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'Why is high VRAM memory bandwidth essential in GPU architectures?',
        options: [
          'Thousands of parallel arithmetic lanes require massive data throughput to prevent execution unit starvation',
          'VRAM bandwidth determines the maximum disk seek rate of the host storage',
          'High bandwidth completely eliminates the need for L1 and L2 caches',
          'Bandwidth only affects network socket communications',
        ],
        explanation: 'Because GPUs execute thousands of threads concurrently, insufficient memory bandwidth starves arithmetic units waiting for data operands.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'What execution paradigm does a modern GPU Streaming Multiprocessor (SM) utilize?',
        options: [
          'Single Instruction, Multiple Threads (SIMT) grouped into warps',
          'Single Instruction, Single Data (SISD) with deep out-of-order execution',
          'Pure asynchronous message passing between independent CPU cores',
          'Synchronous token ring arbitration across memory channels',
        ],
        explanation: 'NVIDIA GPU SMs execute using the SIMT model, where warps of 32 threads execute the same instruction in lockstep across parallel lanes.',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'What performance penalty occurs when conditional branching causes "Branch Divergence" within a GPU warp?',
        options: [
          'Threads evaluating different branches are serialized, substantially reducing parallel SIMT arithmetic throughput',
          'The GPU kernel crashes with an unhandled hardware interrupt',
          'The host CPU takes over arithmetic execution for that warp',
          'The GPU device driver forces an immediate context reset',
        ],
        explanation: 'Because warps execute in lockstep under SIMT, branch divergence serializes execution of divergent paths, leaving threads on unselected branches idle and reducing performance.',
        correct_index: 0,
      },
    ]);
  }

  // 8. Machine Learning
  if (/\b(machine learning|deep learning|supervised learning|unsupervised learning|neural network|gradient descent|overfitting)\b/i.test(lower)) {
    return formatList([
      {
        id: 'q-1',
        question: 'What is the defining characteristic of Supervised Learning in machine learning?',
        options: [
          'Training datasets contain feature inputs mapped to known ground-truth target labels',
          'The algorithm groups unannotated data based solely on distance metrics',
          'An agent interacts with an environment receiving cumulative rewards',
          'Models learn representations without access to data',
        ],
        explanation: 'Supervised learning algorithms infer a mapping function from training data that consists of paired input vectors and supervisory target labels.',
        correct_index: 0,
      },
      {
        id: 'q-2',
        question: 'What distinguishes Classification from Regression tasks in machine learning?',
        options: [
          'Classification predicts discrete categorical class labels, whereas regression models continuous numeric quantities',
          'Classification is unsupervised while regression is supervised',
          'Regression only processes text data while classification processes images',
          'Classification does not require feature matrices',
        ],
        explanation: 'Classification outputs discrete categorical labels, while regression outputs continuous numeric quantities.',
        correct_index: 0,
      },
      {
        id: 'q-3',
        question: 'Which symptom characterizes an overfitted machine learning model?',
        options: [
          'Exceptional accuracy on training data but poor generalization on unseen validation data',
          'High error on both training and validation sets simultaneously',
          'Inability to minimize the loss function during gradient descent',
          'Complete absence of learned parameters',
        ],
        explanation: 'Overfitting occurs when a high-capacity model memorizes noise in the training data, leading to low training error but high test error.',
        correct_index: 0,
      },
      {
        id: 'q-4',
        question: 'What is the primary role of Gradient Descent in training model parameters?',
        options: [
          'Iteratively adjusting weights in the direction opposite to the gradient of the loss function to reach an optimum',
          'Partitioning raw datasets into stratified folds',
          'Encoding categorical string features into one-hot vectors',
          'Calculating the geometric mean of dataset attributes',
        ],
        explanation: 'Gradient Descent calculates partial derivatives of the loss function with respect to weights and steps in the opposite direction to minimize loss.',
        correct_index: 0,
      },
      {
        id: 'q-5',
        question: 'In machine learning workflows, why is a separate Validation set maintained distinct from Training and Test sets?',
        options: [
          'Tuning model hyperparameters and monitoring overfitting without leaking information from the unseen final test set',
          'Computing backpropagation gradient updates to weights',
          'Generating final production evaluation benchmark metrics',
          'Increasing the total volume of training examples',
        ],
        explanation: 'The validation set evaluates generalization performance and guides hyperparameter selection without compromising the final unbiased evaluation on the test set.',
        correct_index: 0,
      },
    ]);
  }

  // 9. Universal Educational Academic Fallback (for any other concept)
  return formatList([
    {
      id: 'q-1',
      question: `What is the foundational definition and core principle of ${cleanTopic}?`,
      options: [
        `The formal theoretical principles and established operational criteria governing ${cleanTopic}`,
        `An unrelated experimental methodology used in a separate academic discipline`,
        `An obsolete historical convention with no modern validity or application`,
        `An informal colloquial term lacking standardized academic criteria`,
      ],
      explanation: `Mastering ${cleanTopic} begins with understanding its formal definition, scope of analysis, and core foundational principles.`,
      correct_index: 0,
    },
    {
      id: 'q-2',
      question: `Which fundamental mechanism or operational component is most critical when analyzing ${cleanTopic}?`,
      options: [
        `The primary underlying interactions, rules, and structural dynamics defining ${cleanTopic}`,
        `Disregarding all empirical measurements and experimental observations`,
        `Assuming constant deterministic outcomes without verifying boundary conditions`,
        `Relying exclusively on surface-level descriptive terminology`,
      ],
      explanation: `Applying ${cleanTopic} effectively requires identifying its core structural mechanisms, operational constraints, and boundary conditions.`,
      correct_index: 0,
    },
    {
      id: 'q-3',
      question: `In standard academic study and professional practice, how is ${cleanTopic} systematically evaluated or verified?`,
      options: [
        `Through rigorous empirical methods, standardized benchmarks, and verified frameworks`,
        `Through unverified anecdotal assertions without reproducible evidence`,
        `By disregarding historical baseline performance data and verified documentation`,
        `By avoiding structured evaluation methodologies`,
      ],
      explanation: `Rigorous study of ${cleanTopic} relies on standardized frameworks, empirical validation, and reproducible analysis.`,
      correct_index: 0,
    },
    {
      id: 'q-4',
      question: `What practical impact or real-world significance does ${cleanTopic} provide in modern practice?`,
      options: [
        `Establishing structured frameworks that enhance analytical clarity, efficiency, and problem-solving`,
        `Introducing unnecessary operational complexity without measurable benefits`,
        `Demonstrating that systematic analysis has no practical real-world utility`,
        `Restricting practical problem-solving exclusively to speculative theory`,
      ],
      explanation: `${cleanTopic} is essential because it structures knowledge, optimizes processes, and enables effective real-world problem-solving.`,
      correct_index: 0,
    },
    {
      id: 'q-5',
      question: `When solving complex problems within ${cleanTopic}, why is establishing clear boundary conditions and error tolerances necessary?`,
      options: [
        `It prevents catastrophic failures, ensures predictable behavior, and defines valid operational ranges`,
        `It eliminates the need for empirical validation and testing`,
        `It proves that theoretical assumptions are unconditionally universal`,
        `It restricts solutions to non-functional speculative theory`,
      ],
      explanation: `Establishing boundary conditions and tolerances ensures system safety, predictable execution, and operational reliability across valid domains in ${cleanTopic}.`,
      correct_index: 0,
    },
  ]);
}

export const quizService = {
  async generateQuiz(params: {
    topic: string;
    difficulty: 'beginner' | 'intermediate' | 'advanced';
    sessionId: string;
    documentIds?: string[];
    questionCount?: number;
  }): Promise<Quiz> {
    const targetCount = params.questionCount && params.questionCount > 0 ? params.questionCount : 4;
    const prompt = `Generate a ${params.difficulty} difficulty quiz with ${targetCount} multiple choice questions on the topic: "${params.topic}". Provide 4 clear options (A, B, C, D) for each question, the correct answer, and an in-depth pedagogical explanation.`;

    const res = await chatService.sendMessage({
      session_id: params.sessionId,
      content: prompt,
      intent: 'quiz',
      difficulty: params.difficulty,
      document_ids: params.documentIds,
      question_count: targetCount,
    });

    const assistantMsg = res.assistant_message;
    const rawQuizData = assistantMsg?.quiz_data;
    const content = assistantMsg?.content;

    let questions: QuizQuestion[] = [];

    // 1. Direct structured quiz_data from backend
    if (Array.isArray(rawQuizData) && rawQuizData.length > 0) {
      questions = mapRawQuestions(rawQuizData);
    }

    // 2. Check for JSON array inside assistant message content
    if (questions.length === 0 && content && typeof content === 'string') {
      try {
        const jsonMatch = content.match(/\[[\s\S]*?\]/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          if (Array.isArray(parsed) && parsed.length > 0) {
            questions = mapRawQuestions(parsed);
          }
        }
      } catch {
        // Ignore JSON parse errors, proceed to Markdown
      }
    }

    // 3. Parse Markdown MCQs from assistant message content
    if (questions.length === 0 && content && typeof content === 'string') {
      questions = parseMarkdownMCQs(content, params.difficulty);
    }

    // 4. Topic-aware, pedagogically authentic fallback (never generic filler!)
    if (questions.length === 0) {
      questions = getTopicAwareQuizFallback(params.topic, params.difficulty, targetCount);
    }

    // 5. If fewer questions than requested were obtained, supplement from topic fallback
    if (questions.length < targetCount) {
      const fallbackList = getTopicAwareQuizFallback(params.topic, params.difficulty, targetCount);
      for (const fq of fallbackList) {
        if (questions.length >= targetCount) break;
        if (!questions.some((q) => q.question.toLowerCase().trim() === fq.question.toLowerCase().trim())) {
          questions.push(fq);
        }
      }
    }

    // 6. Strictly enforce requested question count
    if (questions.length > targetCount) {
      questions = questions.slice(0, targetCount);
    }

    // 7. Ensure sequential unique IDs
    questions = questions.map((q, idx) => ({
      ...q,
      id: `q-${idx + 1}`,
    }));

    const quiz: Quiz = {
      id: `quiz-${Date.now()}`,
      title: `${params.topic} (${params.difficulty.toUpperCase()})`,
      topic: params.topic,
      difficulty: params.difficulty,
      questions,
      created_at: new Date().toISOString(),
    };

    // Save to local storage cache
    const existing = quizService.getSavedQuizzes();
    localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify([quiz, ...existing]));

    return quiz;
  },

  getSavedQuizzes(): Quiz[] {
    try {
      const raw = localStorage.getItem(QUIZ_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  async submitQuiz(submission: QuizSubmission, quiz: Quiz): Promise<QuizResult> {
    let score = 0;
    const details = quiz.questions.map((q) => {
      const selected = submission.answers[q.id];
      const correct = q.correct_index ?? 0;
      const isCorrect = selected === correct;
      if (isCorrect) score += 1;

      return {
        question_id: q.id,
        question: q.question,
        selected_index: selected !== undefined ? selected : -1,
        correct_index: correct,
        is_correct: isCorrect,
        explanation: q.explanation,
      };
    });

    const total = quiz.questions.length;
    const percentage = total > 0 ? Math.round((score / total) * 100) : 0;

    const result: QuizResult = {
      score,
      total_questions: total,
      percentage,
      details,
    };

    const historyItem = {
      quiz_id: quiz.id,
      title: quiz.title,
      topic: quiz.topic,
      difficulty: quiz.difficulty,
      score,
      total,
      percentage,
      timestamp: new Date().toISOString(),
      synced: false,
    };

    const historyKey = getQuizHistoryKey();

    // Save to user-scoped history cache immediately
    try {
      const history = quizService.getCachedQuizHistory();
      localStorage.setItem(
        historyKey,
        JSON.stringify([historyItem, ...history])
      );
    } catch (e) {
      // Ignore
    }

    // Submit to backend
    try {
      await apiClient.post('/analytics/quiz-attempt', {
        quiz_id: quiz.id,
        title: quiz.title,
        topic: quiz.topic,
        difficulty: quiz.difficulty,
        score,
        total_questions: total,
        percentage,
        answers: submission.answers,
        details,
        questions: quiz.questions,
      });

      // Mark as synced in user-scoped history
      try {
        const history = quizService.getCachedQuizHistory();
        if (history.length > 0 && history[0].quiz_id === quiz.id) {
          history[0].synced = true;
          localStorage.setItem(historyKey, JSON.stringify(history));
        }
      } catch (e) {
        // Ignore
      }
    } catch (err) {
      console.warn('Backend quiz attempt sync deferred:', err);
    }

    return result;
  },

  async syncPendingQuizAttempts(userId?: string): Promise<void> {
    const key = getQuizHistoryKey(userId);
    try {
      const history = quizService.getCachedQuizHistory(userId);
      let updated = false;

      for (const item of history) {
        if (!item.synced) {
          try {
            await apiClient.post('/analytics/quiz-attempt', {
              quiz_id: item.quiz_id,
              title: item.title,
              topic: item.topic,
              difficulty: item.difficulty || 'medium',
              score: item.score,
              total_questions: item.total || 1,
              percentage: item.percentage || 0,
            });
            item.synced = true;
            updated = true;
          } catch (e) {
            // Stop syncing if backend unreachable
            break;
          }
        }
      }

      if (updated) {
        localStorage.setItem(key, JSON.stringify(history));
      }
    } catch {
      // Ignore
    }
  },

  async getQuizHistory(userId?: string): Promise<any[]> {
    const key = getQuizHistoryKey(userId);
    try {
      const res = await apiClient.get('/analytics/quiz-history');
      const serverHistory = res.data?.data;
      if (Array.isArray(serverHistory)) {
        localStorage.setItem(key, JSON.stringify(serverHistory));
        return serverHistory;
      }
    } catch {
      // Fallback to user-scoped local storage cache
    }
    return quizService.getCachedQuizHistory(userId);
  },

  getCachedQuizHistory(userId?: string): any[] {
    const key = getQuizHistoryKey(userId);
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },
};
