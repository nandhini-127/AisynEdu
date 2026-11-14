"""
Generates 3 rich educational sample PDFs for testing and evaluating EduNex AI RAG pipeline.
"""
import os
from pathlib import Path


def create_sample_pdfs():
    import fitz  # PyMuPDF

    output_dir = Path(__file__).resolve().parent.parent / "data" / "sample_pdfs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Computer Networks PDF
    cn_doc = fitz.open()
    cn_doc.set_metadata({
        "title": "Computer Networks: Architecture and Protocols",
        "author": "Dr. Alex Reynolds",
        "subject": "Computer Science",
    })

    # Page 1
    p1 = cn_doc.new_page()
    p1_text = """COMPUTER NETWORKS & LAYERED ARCHITECTURE
Chapter 1: The OSI 7-Layer Reference Model

A computer network is an interconnected collection of autonomous computing nodes that exchange data over transmission media. To manage network complexity, the International Organization for Standardization (ISO) designed the Open Systems Interconnection (OSI) 7-layer reference model.

Layer 7 - Application Layer: Provides network services directly to end-user applications. Key protocols include HTTP for web browsing, SMTP for email delivery, and FTP for file transfers.
Layer 6 - Presentation Layer: Handles data translation, character encoding, compression, and encryption/decryption (such as TLS/SSL).
Layer 5 - Session Layer: Establishes, manages, maintains, and terminates communication sessions between applications.
Layer 4 - Transport Layer: Manages end-to-end communication, segmentation, flow control, and error recovery. Major protocols are TCP and UDP.
Layer 3 - Network Layer: Responsible for logical packet addressing and routing across heterogeneous networks. The Internet Protocol (IP) operates here.
Layer 2 - Data Link Layer: Transmits frames between adjacent network nodes over a physical link, handling physical MAC addressing and error detection via CRC.
Layer 1 - Physical Layer: Transmits raw, unstructured bit streams over a physical transmission medium (copper cable, optical fiber, radio frequencies).
"""
    p1.insert_text(fitz.Point(50, 60), p1_text, fontsize=11)

    # Page 2
    p2 = cn_doc.new_page()
    p2_text = """Chapter 2: Transport Layer - TCP versus UDP

The transport layer delivers segments between host processes using port numbers.

Transmission Control Protocol (TCP):
TCP is a connection-oriented, reliable transport protocol. Before data transmission begins, TCP establishes a connection using the Three-Way Handshake:
1. SYN: The client transmits a segment with SYN flag set and an initial sequence number (ISN).
2. SYN-ACK: The server responds acknowledging client ISN and offering its own server ISN.
3. ACK: The client acknowledges the server sequence number.

TCP guarantees in-order delivery and reliability through sequence numbers, cumulative acknowledgments, and retransmission timeouts. TCP implements Flow Control using a sliding window advertised by the receiver, preventing the sender from overwhelming receiver buffer space. TCP also features Congestion Control algorithms including Slow Start, Congestion Avoidance, Fast Retransmit, and Fast Recovery.

User Datagram Protocol (UDP):
UDP is a connectionless, lightweight, best-effort transport protocol. It does not establish a handshake, maintain connection state, or guarantee packet delivery or ordering. UDP has a minimal header size of 8 bytes compared to TCP's 20-60 bytes. UDP is ideal for latency-sensitive applications like VoIP, video streaming, online gaming, and DNS lookups.
"""
    p2.insert_text(fitz.Point(50, 60), p2_text, fontsize=11)

    # Page 3
    p3 = cn_doc.new_page()
    p3_text = """Chapter 3: Network Layer, Routing & Domain Name System (DNS)

Logical Addressing:
IPv4 addresses are 32-bit values divided into four 8-bit octets (e.g., 192.168.1.1). Classless Inter-Domain Routing (CIDR) uses slash notation (/24) to denote network prefix length. IPv6 provides a 128-bit address space, resolving IPv4 address exhaustion.

Routing Algorithms:
Routers forward packets across networks using routing tables determined by algorithms:
- Distance Vector Routing: Nodes periodically broadcast their routing tables to immediate neighbors. The Bellman-Ford algorithm is used. Routing Information Protocol (RIP) uses hop count as metric, limited to 15 hops.
- Link State Routing: Every node floods information about its active links across the entire network. Each router constructs a complete network topology map and executes Dijkstra's Shortest Path First algorithm. Open Shortest Path First (OSPF) is a link-state interior gateway protocol.

Domain Name System (DNS):
DNS translates human-readable domain names (such as example.com) into numerical IP addresses. DNS operates hierarchically:
Root Name Servers -> Top-Level Domain (TLD) Servers (.com, .org) -> Authoritative Name Servers.
Recursive resolvers query through this hierarchy and cache results using Time-To-Live (TTL) values.
"""
    p3.insert_text(fitz.Point(50, 60), p3_text, fontsize=11)

    cn_path = output_dir / "computer_networks.pdf"
    cn_doc.save(str(cn_path))
    cn_doc.close()
    print(f"Generated: {cn_path}")

    # 2. Operating Systems PDF
    os_doc = fitz.open()
    os_doc.set_metadata({
        "title": "Operating Systems: Principles and Architecture",
        "author": "Prof. Marcus Vance",
        "subject": "Computer Science",
    })

    # Page 1
    p1 = os_doc.new_page()
    p1_text = """OPERATING SYSTEMS: CONCURRENCY & ARCHITECTURE
Chapter 1: Processes and Process Management

An operating system acts as an intermediary between computer hardware and user applications. The core abstraction for program execution is the Process: a program in execution containing program code, program counter, registers, stack, and heap.

Process State Lifecycle:
A process transitions through several fundamental states:
1. New: The process is being created.
2. Ready: The process is in memory, waiting to be assigned to a CPU core.
3. Running: Instructions are actively executing on the processor.
4. Waiting (Blocked): The process is waiting for an I/O event or signal.
5. Terminated: The process has finished execution and operating system resources are reclaimed.

Process Control Block (PCB):
The kernel maintains a PCB for each process, storing Process ID (PID), program counter, CPU registers, scheduling priority, memory management pointers, and open file descriptors.
A Context Switch occurs when the CPU switches from executing one process to another, saving the current process state into its PCB and restoring the state of the scheduled process. Context switching is pure overhead during which no useful application work occurs.
"""
    p1.insert_text(fitz.Point(50, 60), p1_text, fontsize=11)

    # Page 2
    p2 = os_doc.new_page()
    p2_text = """Chapter 2: CPU Scheduling and Synchronization

CPU Scheduling:
The CPU scheduler selects a process from the ready queue for execution:
- First-Come, First-Served (FCFS): Non-preemptive, suffers from the Convoy Effect where short processes wait behind long ones.
- Shortest Job First (SJF): Schedules process with smallest next CPU burst. Optimal for minimizing average waiting time, but difficult to predict burst lengths.
- Round Robin (RR): Preemptive scheduling where each process receives a fixed time slice (time quantum). Excellent for interactive timesharing systems.
- Priority Scheduling: Processes execute according to priority numbers; Starvation is mitigated using Aging (gradually increasing priority of waiting processes).

Synchronization & Race Conditions:
A race condition occurs when concurrent threads access shared data and the final outcome depends on execution timing. The Critical Section is code modifying shared variables.
Solutions must satisfy: Mutual Exclusion, Progress, and Bounded Waiting.
Synchronization Primitives:
- Mutex: A locking mechanism providing mutual exclusion where only the thread acquiring the lock may release it.
- Semaphores: Integer variables accessed via wait() / P() and signal() / V() operations. Counting semaphores manage finite resource pools, while binary semaphores act similarly to mutexes.
"""
    p2.insert_text(fitz.Point(50, 60), p2_text, fontsize=11)

    # Page 3
    p3 = os_doc.new_page()
    p3_text = """Chapter 3: Deadlocks and Virtual Memory Management

Deadlocks:
A deadlock is a situation where every process in a set is waiting for an event that only another process in the set can cause.
Coffman's Four Deadlock Conditions (all must hold simultaneously):
1. Mutual Exclusion: At least one resource is held in non-shareable mode.
2. Hold and Wait: A process holds resources while requesting additional resources.
3. No Preemption: Resources cannot be forcibly taken; only released voluntarily.
4. Circular Wait: A closed chain of processes exists where each waits for a resource held by the next.

Deadlock Avoidance:
The Banker's Algorithm evaluates resource allocation safety before granting requests, ensuring the system never enters an unsafe state.

Virtual Memory and Paging:
Virtual memory separates user logical memory from physical memory (RAM).
Paging divides physical memory into fixed-size Frames and logical memory into Pages of equal size (commonly 4 KB).
The Memory Management Unit (MMU) uses Page Tables to translate virtual addresses into physical addresses.
A Translation Lookaside Buffer (TLB) is a fast hardware associative cache storing recent virtual-to-physical translations to reduce memory access latency.
When a requested page is not in RAM, a Page Fault occurs, triggering OS retrieval from secondary storage. Page replacement algorithms include FIFO, Least Recently Used (LRU), and Optimal (OPT).
"""
    p3.insert_text(fitz.Point(50, 60), p3_text, fontsize=11)

    os_path = output_dir / "operating_systems.pdf"
    os_doc.save(str(os_path))
    os_doc.close()
    print(f"Generated: {os_path}")

    # 3. Machine Learning PDF
    ml_doc = fitz.open()
    ml_doc.set_metadata({
        "title": "Machine Learning: Foundations and Deep Neural Architectures",
        "author": "Dr. Sophia Chen",
        "subject": "Artificial Intelligence",
    })

    # Page 1
    p1 = ml_doc.new_page()
    p1_text = """FOUNDATIONS OF MACHINE LEARNING & DEEP LEARNING
Chapter 1: Supervised and Unsupervised Paradigms

Machine Learning is a discipline of artificial intelligence enabling computational models to learn patterns from empirical data without being explicitly programmed.

Supervised Learning:
Supervised learning trains models on labeled input-output pairs (X, y).
- Regression: Predicts continuous numerical targets. Common algorithms include Ordinary Least Squares (OLS) Linear Regression, Ridge Regression, and Support Vector Regression (SVR).
- Classification: Predicts discrete categorical labels. Common algorithms include Logistic Regression, Support Vector Machines (SVM), Decision Trees, and ensemble methods such as Random Forests and Gradient Boosted Decision Trees (XGBoost, LightGBM).

Unsupervised Learning:
Unsupervised learning discovers hidden structure, clusters, or representations in unlabeled data (X).
- Clustering: Groups similar observations. K-Means clustering partitions data into K centroids by minimizing inertia (within-cluster sum of squares). Hierarchical clustering builds dendrogram trees.
- Dimensionality Reduction: Compresses high-dimensional feature spaces while preserving variance. Principal Component Analysis (PCA) performs orthogonal linear transformations to find principal eigenvectors of the covariance matrix.
"""
    p1.insert_text(fitz.Point(50, 60), p1_text, fontsize=11)

    # Page 2
    p2 = ml_doc.new_page()
    p2_text = """Chapter 2: Optimization, Overfitting & Regularization

Optimization:
Models minimize an objective Loss Function:
- Mean Squared Error (MSE) for regression tasks.
- Cross-Entropy Loss (Log Loss) for classification tasks.

Optimization Algorithms:
- Stochastic Gradient Descent (SGD): Updates weights iteratively along the negative gradient of the loss function.
- Adam (Adaptive Moment Estimation): Combines momentum with adaptive learning rates computed from first and second moments of the gradients.

Generalization and Overfitting:
- Overfitting occurs when a model learns noise and training idiosyncrasies, showing low training loss but high validation loss (high variance).
- Underfitting occurs when the model is insufficiently expressive, resulting in high training loss (high bias). This trade-off is the Bias-Variance Dilemma.

Regularization Techniques:
1. L1 Regularization (Lasso): Adds penalty proportional to absolute weight magnitudes (lambda * |w|), driving irrelevant weights to exact zero and performing feature selection.
2. L2 Regularization (Ridge): Adds penalty proportional to squared weight magnitudes (lambda * w^2), shrinking weights smoothly and stabilizing multi-collinearity.
3. Dropout: Randomly deactivates a fraction p of neurons during each training step, preventing co-adaptation of features.
4. Early Stopping: Halts training when validation loss stops improving.
"""
    p2.insert_text(fitz.Point(50, 60), p2_text, fontsize=11)

    # Page 3
    p3 = ml_doc.new_page()
    p3_text = """Chapter 3: Deep Learning and Attention Mechanisms

Neural Network Foundations:
Artificial Neural Networks (ANNs) stack linear transformations with non-linear activation functions (ReLU, GELU, Sigmoid) to approximate arbitrary functions according to the Universal Approximation Theorem.
Convolutional Neural Networks (CNNs) utilize spatial parameter sharing and pooling layers, dominating computer vision tasks.

The Transformer Architecture & Self-Attention:
Introduced by Vaswani et al. (2017) in 'Attention Is All You Need', the Transformer replaced recurrent architectures with Self-Attention mechanisms, enabling massive parallelization during training.

Scaled Dot-Product Attention:
Input vectors are linearly projected into three matrices: Queries (Q), Keys (K), and Values (V) of dimension d_k:
Attention(Q, K, V) = softmax( (Q * K^T) / sqrt(d_k) ) * V
The division by sqrt(d_k) scales dot products to prevent softmax gradients from vanishing in high dimensions.

Multi-Head Attention:
Multi-Head Attention runs multiple parallel attention projections (heads), allowing the model to jointly attend to information from different representation subspaces at different positions.

Positional Encoding:
Because Transformers process sequence tokens simultaneously without recurrence, Positional Encodings (sinusoidal functions or learned embeddings) are added to input embeddings to inject token sequence order.
Transformers form the foundation of modern Large Language Models (LLMs) such as Gemini, GPT-4, and Claude.
"""
    p3.insert_text(fitz.Point(50, 60), p3_text, fontsize=11)

    ml_path = output_dir / "machine_learning.pdf"
    ml_doc.save(str(ml_path))
    ml_doc.close()
    print(f"Generated: {ml_path}")


if __name__ == "__main__":
    create_sample_pdfs()

