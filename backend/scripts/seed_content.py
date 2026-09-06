"""Realistic AUST CSE seed content for `seed_production.py` (no "demo" labels).

Structure per course: outcomes, CO→PO map, syllabus topics + text, question papers (past = faculty-tagged
ground truth, draft = left un-mapped so the AI stage is real), optional marks sheet spec, rubric and answers.
Drafts carry deliberate but plausible flaws (an uncovered CO, a near-duplicate, a marks mismatch) so every
module has something to find. Student ids are anonymised (SEC-007).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------------------------------------
ACCOUNTS: list[dict] = [
    {"email": "rezwana.karim@aust.edu", "full_name": "Dr. Rezwana Karim", "role": "faculty", "title": "Professor, CSE"},
    {"email": "mahmudul.hasan@aust.edu", "full_name": "Dr. Mahmudul Hasan", "role": "faculty", "title": "Associate Professor, CSE"},
    {"email": "farhana.islam@aust.edu", "full_name": "Farhana Islam", "role": "faculty", "title": "Assistant Professor, CSE"},
    {"email": "tanvir.ahmed@aust.edu", "full_name": "Tanvir Ahmed", "role": "faculty", "title": "Lecturer, CSE"},
    {"email": "head.cse@aust.edu", "full_name": "Prof. Dr. Md. Shahriar Mahbub", "role": "admin", "title": "Head, Department of CSE"},
    {"email": "obe.cell@aust.edu", "full_name": "Nusrat Jahan", "role": "admin", "title": "OBE & Accreditation Cell"},
]

# ---------------------------------------------------------------------------------------------------------
# Courses  (owner = account email)
# ---------------------------------------------------------------------------------------------------------
# CSE 3103 (Dr. Rezwana Karim) is loaded from data/seed-data (3 papers, marks CSV, rubric + 6 scripts × 2 graders)
# by the runner; everything below is authored here.

COURSES: list[dict] = [
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "rezwana.karim@aust.edu",
        "code": "CSE 4101",
        "title": "Software Engineering",
        "term": "Fall 2025",
        "description": "Software process models, requirements engineering, UML-based analysis and design, architectural and "
                       "design patterns, verification and validation, project management and software quality.",
        "outcomes": [
            ("CO1", "Explain software process models and select an appropriate model for a given project context.", "understand", 15),
            ("CO2", "Elicit, analyse and specify software requirements using use cases and user stories.", "apply", 20),
            ("CO3", "Design software systems with UML class, sequence and state diagrams applying design principles.", "apply", 25),
            ("CO4", "Analyse software architecture and design-pattern choices against quality attributes.", "analyze", 20),
            ("CO5", "Plan verification and validation activities and derive test cases from requirements.", "apply", 10),
            ("CO6", "Estimate effort and schedule and assess risks in a software project.", "evaluate", 10),
        ],
        "co_po": {"CO1": [("PO1", 2)], "CO2": [("PO2", 3), ("PO10", 1)], "CO3": [("PO3", 3), ("PO5", 2)],
                  "CO4": [("PO2", 2), ("PO3", 2)], "CO5": [("PO4", 2), ("PO5", 1)], "CO6": [("PO11", 3), ("PO9", 1)]},
        "topics": [
            ("T-01", "Software engineering fundamentals, software crisis and ethics"),
            ("T-02", "Process models: waterfall, incremental, spiral, agile and Scrum"),
            ("T-03", "Requirements elicitation techniques and stakeholder analysis"),
            ("T-04", "Requirements specification: use cases, user stories, SRS"),
            ("T-05", "UML structural modelling: class and object diagrams"),
            ("T-06", "UML behavioural modelling: sequence, activity and state diagrams"),
            ("T-07", "Design principles: cohesion, coupling, SOLID"),
            ("T-08", "Architectural styles: layered, client-server, MVC, microservices"),
            ("T-09", "Design patterns: creational, structural, behavioural"),
            ("T-10", "Software testing: unit, integration, system, black-box and white-box"),
            ("T-11", "Verification and validation, reviews and inspections"),
            ("T-12", "Project management: estimation (COCOMO, function points), scheduling"),
            ("T-13", "Risk management and software quality assurance"),
            ("T-14", "Software maintenance, configuration management and DevOps basics"),
        ],
        "papers": [
            {
                "label": "Final Examination, Fall 2024", "year": 2024, "term": "Fall 2024", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1(a)", "Compare the waterfall and spiral process models. Under what project conditions would you recommend each?", 6, "CO1"),
                    ("1(b)", "Describe the roles and ceremonies of Scrum and explain how it handles changing requirements.", 4, "CO1"),
                    ("2(a)", "Write a use-case description (main and alternative flows) for 'Borrow a book' in a university library system.", 6, "CO2"),
                    ("2(b)", "Distinguish functional from non-functional requirements with two examples of each for an online exam portal.", 4, "CO2"),
                    ("3", "Draw a UML class diagram for a ride-sharing application showing Rider, Driver, Trip, Payment and Rating with multiplicities and at least one inheritance relationship.", 10, "CO3"),
                    ("4", "Draw a sequence diagram for the 'checkout' scenario of an e-commerce system involving Cart, Order, PaymentGateway and Inventory.", 10, "CO3"),
                    ("5", "Analyse how the layered and microservices architectural styles trade off modifiability, performance and deployability for a hospital management system.", 10, "CO4"),
                    ("6(a)", "Derive equivalence classes and boundary values for a function that accepts a percentage mark (0-100) and returns a letter grade.", 6, "CO5"),
                    ("6(b)", "Explain how the Observer pattern reduces coupling; illustrate with a stock-price dashboard.", 4, "CO4"),
                ],
            },
            {
                "label": "Final Examination, Spring 2026", "year": 2026, "term": "Spring 2026", "declared_total": 60, "is_draft": True,
                "questions": [
                    ("1(a)", "Define software engineering. List the phases of the waterfall model.", 5, None),
                    ("1(b)", "State the four values of the Agile Manifesto.", 5, None),
                    ("2(a)", "Write a use-case description with main and alternative flows for 'Borrow a book' in a university library system.", 6, None),
                    ("2(b)", "List five elicitation techniques and describe when each is appropriate.", 4, None),
                    ("3", "Draw a UML class diagram for a food-delivery application showing Customer, Restaurant, Order, Rider and Payment with multiplicities.", 10, None),
                    ("4", "Draw a state diagram for an Order in an e-commerce system from creation to delivery or cancellation.", 10, None),
                    ("5", "Define cohesion and coupling. Name the SOLID principles.", 10, None),
                    ("6(a)", "Explain black-box and white-box testing with one example each.", 5, None),
                    ("6(b)", "Describe the Singleton and Factory Method patterns.", 5, None),
                ],
            },
        ],
        "marks": {"paper": 0, "students": 28, "ability": {"CO1": 0.78, "CO2": 0.72, "CO3": 0.66, "CO4": 0.47, "CO5": 0.74, "CO6": 0.70}, "term": "Fall 2024"},
    },
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "mahmudul.hasan@aust.edu",
        "code": "CSE 2201",
        "title": "Data Structures and Algorithms",
        "term": "Spring 2026",
        "description": "Asymptotic analysis; arrays, linked lists, stacks, queues; trees, heaps, hashing; graphs and traversals; "
                       "sorting and searching; greedy and divide-and-conquer paradigms.",
        "outcomes": [
            ("CO1", "Analyse the time and space complexity of iterative and recursive algorithms using asymptotic notation.", "analyze", 20),
            ("CO2", "Implement linear data structures (arrays, linked lists, stacks, queues) and apply them to problems.", "apply", 20),
            ("CO3", "Implement and apply tree and heap structures including BST, AVL and priority queues.", "apply", 20),
            ("CO4", "Apply hashing techniques and analyse collision-resolution strategies.", "apply", 10),
            ("CO5", "Apply graph representations and traversal algorithms to model and solve problems.", "apply", 20),
            ("CO6", "Compare sorting and searching algorithms and select an appropriate one for a given constraint.", "evaluate", 10),
        ],
        "co_po": {"CO1": [("PO1", 3), ("PO2", 2)], "CO2": [("PO1", 2), ("PO3", 2)], "CO3": [("PO3", 3)],
                  "CO4": [("PO1", 2)], "CO5": [("PO2", 3), ("PO3", 2)], "CO6": [("PO2", 2), ("PO4", 1)]},
        "topics": [
            ("T-01", "Algorithm analysis: Big-O, Omega, Theta; recurrence relations"),
            ("T-02", "Arrays, dynamic arrays and amortised analysis"),
            ("T-03", "Singly, doubly and circular linked lists"),
            ("T-04", "Stacks and queues; expression evaluation; deque"),
            ("T-05", "Recursion and backtracking"),
            ("T-06", "Binary trees and traversals"),
            ("T-07", "Binary search trees; AVL rotations"),
            ("T-08", "Heaps and priority queues; heapsort"),
            ("T-09", "Hashing: hash functions, chaining, open addressing"),
            ("T-10", "Graph representations; BFS and DFS"),
            ("T-11", "Shortest paths: Dijkstra; minimum spanning trees: Prim, Kruskal"),
            ("T-12", "Sorting: insertion, merge, quick, counting, radix"),
            ("T-13", "Searching: binary search and its variants"),
            ("T-14", "Divide and conquer and greedy paradigms"),
        ],
        "papers": [
            {
                "label": "Final Examination, Spring 2025", "year": 2025, "term": "Spring 2025", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1(a)", "Solve the recurrence T(n) = 2T(n/2) + n using the master theorem and state the tight bound.", 5, "CO1"),
                    ("1(b)", "Analyse the worst-case and amortised cost of appending to a dynamic array that doubles when full.", 5, "CO1"),
                    ("2", "Write a function to reverse a singly linked list in place and trace it on the list 3→7→1→9.", 10, "CO2"),
                    ("3(a)", "Convert the infix expression A + B * (C - D) / E to postfix using a stack, showing each step.", 5, "CO2"),
                    ("3(b)", "Insert the keys 50, 30, 70, 20, 40, 60, 80, 10 into an empty AVL tree, showing every rotation.", 5, "CO3"),
                    ("4", "Build a max-heap from the array [4, 10, 3, 5, 1, 8, 12] using bottom-up heapify and then perform two delete-max operations.", 10, "CO3"),
                    ("5", "Insert the keys 23, 43, 13, 27, 33 into a hash table of size 10 using (i) chaining and (ii) linear probing with h(k) = k mod 10. Compare the resulting load and probe counts.", 10, "CO4"),
                    ("6", "For the given weighted graph, run Dijkstra's algorithm from vertex A, showing the distance table after each step, and state the shortest path to F.", 10, "CO5"),
                ],
            },
            {
                "label": "Final Examination, Spring 2026", "year": 2026, "term": "Spring 2026", "declared_total": 60, "is_draft": True,
                "questions": [
                    ("1(a)", "Define Big-O, Big-Omega and Big-Theta notation with one example each.", 5, None),
                    ("1(b)", "State the master theorem and its three cases.", 5, None),
                    ("2", "Write a function to reverse a singly linked list in place and trace it on the list 5→2→8→6.", 10, None),
                    ("3", "Convert the infix expression (A + B) * C - D / E to postfix using a stack, showing the stack after each token.", 10, None),
                    ("4", "Insert the keys 40, 20, 60, 10, 30, 50, 70, 5 into an empty AVL tree, showing every rotation.", 10, None),
                    ("5", "Perform BFS and DFS on the given undirected graph starting from vertex 1 and list the visiting order for each.", 8, None),
                    ("6", "Trace merge sort on the array [38, 27, 43, 3, 9, 82, 10] and state its time complexity.", 10, None),
                ],
            },
        ],
        "marks": {"paper": 0, "students": 30, "ability": {"CO1": 0.55, "CO2": 0.76, "CO3": 0.70, "CO4": 0.79, "CO5": 0.52, "CO6": 0.70}, "term": "Spring 2025"},
    },
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "mahmudul.hasan@aust.edu",
        "code": "CSE 3201",
        "title": "Operating Systems",
        "term": "Spring 2026",
        "description": "Processes and threads, CPU scheduling, synchronisation and deadlock, memory management and virtual memory, "
                       "file systems and I/O, protection and security.",
        "outcomes": [
            ("CO1", "Describe operating-system structures, system calls and the process/thread model.", "understand", 15),
            ("CO2", "Apply CPU-scheduling algorithms and compute performance metrics.", "apply", 20),
            ("CO3", "Solve synchronisation problems using semaphores and monitors and analyse deadlock conditions.", "analyze", 25),
            ("CO4", "Apply paging, segmentation and page-replacement algorithms to memory-management problems.", "apply", 25),
            ("CO5", "Explain file-system organisation, disk scheduling and protection mechanisms.", "understand", 15),
        ],
        "co_po": {"CO1": [("PO1", 2)], "CO2": [("PO1", 2), ("PO2", 2)], "CO3": [("PO2", 3), ("PO3", 1)],
                  "CO4": [("PO1", 2), ("PO2", 2)], "CO5": [("PO1", 2), ("PO6", 1)]},
        "topics": [
            ("T-01", "OS services, system calls, kernel structures"),
            ("T-02", "Processes, PCB, context switching, IPC"),
            ("T-03", "Threads and multithreading models"),
            ("T-04", "CPU scheduling: FCFS, SJF, SRTF, RR, priority, multilevel queues"),
            ("T-05", "Critical-section problem, Peterson's solution, hardware support"),
            ("T-06", "Semaphores, monitors, classic synchronisation problems"),
            ("T-07", "Deadlock: characterisation, prevention, avoidance (Banker's), detection"),
            ("T-08", "Main memory: contiguous allocation, paging, segmentation"),
            ("T-09", "Virtual memory: demand paging, page replacement (FIFO, LRU, Optimal), thrashing"),
            ("T-10", "File-system interface and implementation, allocation methods"),
            ("T-11", "Mass storage, disk scheduling, RAID"),
            ("T-12", "Protection and security basics"),
        ],
        "papers": [
            {
                "label": "Final Examination, Fall 2025", "year": 2025, "term": "Fall 2025", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1(a)", "Explain the steps of a system call with the transition between user mode and kernel mode.", 5, "CO1"),
                    ("1(b)", "Compare user-level and kernel-level threads and describe the many-to-one and one-to-one models.", 5, "CO1"),
                    ("2", "Five processes arrive at times 0, 1, 2, 3, 4 with burst times 8, 4, 9, 5, 2. Draw Gantt charts for SRTF and Round Robin (quantum 3) and compute the average waiting and turnaround times for each.", 12, "CO2"),
                    ("3(a)", "Write a semaphore-based solution to the bounded-buffer producer-consumer problem and explain why each semaphore is needed.", 8, "CO3"),
                    ("3(b)", "Given the allocation, max and available matrices below for five processes and three resource types, apply the Banker's algorithm to decide whether the state is safe and give a safe sequence.", 8, "CO3"),
                    ("4(a)", "A system uses 32-bit logical addresses and 4 KB pages. Compute the number of pages, the page-offset bits and the page-table size if each entry is 4 bytes.", 6, "CO4"),
                    ("4(b)", "For the reference string 7 0 1 2 0 3 0 4 2 3 0 3 2 with 3 frames, count page faults under FIFO, LRU and Optimal replacement.", 8, "CO4"),
                    ("5", "Compare contiguous, linked and indexed file allocation with respect to random access, fragmentation and file growth.", 8, "CO5"),
                ],
            },
            {
                "label": "Mid Term Examination, Spring 2026", "year": 2026, "term": "Spring 2026", "declared_total": 30, "is_draft": True,
                "questions": [
                    ("1(a)", "Define process and thread. List the states in the five-state process model.", 4, None),
                    ("1(b)", "List four services provided by an operating system.", 3, None),
                    ("2", "Four processes arrive at times 0, 1, 2, 3 with burst times 6, 8, 7, 3. Draw Gantt charts for FCFS and SJF (non-preemptive) and compute the average waiting time for each.", 8, None),
                    ("3", "Write a semaphore-based solution to the bounded-buffer producer-consumer problem and explain the purpose of each semaphore.", 8, None),
                    ("4", "State the four necessary conditions for deadlock. Define a safe state.", 5, None),
                ],
            },
        ],
        "marks": {"paper": 0, "students": 30, "ability": {"CO1": 0.80, "CO2": 0.74, "CO3": 0.49, "CO4": 0.68, "CO5": 0.77}, "term": "Fall 2025"},
    },
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "farhana.islam@aust.edu",
        "code": "CSE 3105",
        "title": "Computer Networks",
        "term": "Spring 2026",
        "description": "Layered network architectures; application, transport, network and link layers; TCP congestion control; "
                       "IP addressing and routing; Ethernet, wireless LANs and basic network security.",
        "outcomes": [
            ("CO1", "Explain the layered architecture of the Internet and the services of each layer.", "understand", 15),
            ("CO2", "Analyse application-layer protocols (HTTP, DNS, SMTP) and their performance.", "analyze", 15),
            ("CO3", "Apply transport-layer concepts: reliable data transfer, flow control and TCP congestion control.", "apply", 25),
            ("CO4", "Design IP addressing schemes with subnetting/CIDR and apply routing algorithms.", "apply", 25),
            ("CO5", "Explain link-layer protocols, switching and wireless LAN operation.", "understand", 10),
            ("CO6", "Evaluate basic network-security mechanisms including symmetric/asymmetric cryptography and TLS.", "evaluate", 10),
        ],
        "co_po": {"CO1": [("PO1", 2)], "CO2": [("PO2", 2)], "CO3": [("PO1", 2), ("PO2", 3)],
                  "CO4": [("PO3", 3), ("PO5", 1)], "CO5": [("PO1", 2)], "CO6": [("PO6", 2), ("PO8", 1)]},
        "topics": [
            ("T-01", "Internet architecture, protocol layering, delay and loss"),
            ("T-02", "HTTP, persistent connections, web caching"),
            ("T-03", "DNS, SMTP, socket programming basics"),
            ("T-04", "UDP, reliable data transfer principles (rdt), Go-Back-N and Selective Repeat"),
            ("T-05", "TCP segment structure, connection management, flow control"),
            ("T-06", "TCP congestion control: slow start, AIMD, fast recovery"),
            ("T-07", "IPv4 datagram, fragmentation, addressing, subnetting and CIDR"),
            ("T-08", "NAT, DHCP, ICMP, IPv6"),
            ("T-09", "Routing algorithms: link-state (Dijkstra) and distance-vector"),
            ("T-10", "Intra- and inter-AS routing: OSPF and BGP"),
            ("T-11", "Link layer: error detection, ALOHA/CSMA/CD, Ethernet, switches, ARP"),
            ("T-12", "Wireless LANs: 802.11 CSMA/CA"),
            ("T-13", "Network security: cryptography, message integrity, TLS"),
        ],
        "papers": [
            {
                "label": "Final Examination, Spring 2025", "year": 2025, "term": "Spring 2025", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1(a)", "Explain the four sources of packet delay and compute the end-to-end delay for a 1 Mbit file over two 10 Mbps links with 2 ms propagation delay each.", 6, "CO1"),
                    ("1(b)", "Compare circuit switching and packet switching for bursty traffic.", 4, "CO1"),
                    ("2", "Analyse the total time to fetch a web page with one base HTML file and four small objects under non-persistent HTTP, persistent HTTP without pipelining and persistent HTTP with pipelining, in terms of RTT.", 10, "CO2"),
                    ("3(a)", "Explain the Go-Back-N and Selective Repeat protocols and compare their behaviour when a single packet is lost with window size 4.", 6, "CO3"),
                    ("3(b)", "Trace TCP congestion window over 16 transmission rounds given ssthresh = 8 MSS and a triple-duplicate-ACK loss at round 9 (TCP Reno).", 8, "CO3"),
                    ("4", "An organisation is allocated 200.15.64.0/22 and needs four subnets with 400, 200, 100 and 50 hosts. Design the subnets giving network address, mask, and usable range for each.", 12, "CO4"),
                    ("5", "Run the distance-vector algorithm on the given 4-node network and show the routing table at node x after convergence. Explain the count-to-infinity problem.", 8, "CO4"),
                    ("6", "Explain how a switch learns MAC addresses and forwards frames. Describe how ARP resolves an IP address on the same subnet.", 6, "CO5"),
                ],
            },
            {
                "label": "Final Examination, Spring 2026", "year": 2026, "term": "Spring 2026", "declared_total": 60, "is_draft": True,
                "questions": [
                    ("1(a)", "List the layers of the Internet protocol stack and state one protocol at each layer.", 5, None),
                    ("1(b)", "Explain the four sources of packet delay and compute the end-to-end delay for a 2 Mbit file over two 10 Mbps links with 2 ms propagation delay each.", 5, None),
                    ("2", "Describe how DNS resolves www.aust.edu using iterative queries; draw the message sequence among the local, root, TLD and authoritative servers.", 10, None),
                    ("3(a)", "Describe TCP's three-way handshake and connection teardown.", 5, None),
                    ("3(b)", "Trace TCP Reno's congestion window over 14 rounds given ssthresh = 8 MSS and a timeout at round 8.", 7, None),
                    ("4", "An organisation is allocated 172.20.8.0/22 and needs subnets for 500, 120, 60 and 30 hosts. Design the addressing plan.", 12, None),
                    ("5", "Run Dijkstra's link-state algorithm from node u on the given network and list the forwarding table at u.", 8, None),
                    ("6", "Explain CSMA/CD and why it cannot be used in 802.11 wireless LANs.", 6, None),
                ],
            },
        ],
        "marks": {"paper": 0, "students": 32, "ability": {"CO1": 0.81, "CO2": 0.69, "CO3": 0.58, "CO4": 0.44, "CO5": 0.75, "CO6": 0.70}, "term": "Spring 2025"},
    },
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "farhana.islam@aust.edu",
        "code": "CSE 4103",
        "title": "Artificial Intelligence",
        "term": "Spring 2026",
        "description": "Intelligent agents, uninformed and informed search, adversarial search, constraint satisfaction, "
                       "propositional and first-order logic, probabilistic reasoning and an introduction to machine learning.",
        "outcomes": [
            ("CO1", "Formulate problems as state-space search and apply uninformed and informed search algorithms.", "apply", 25),
            ("CO2", "Apply adversarial search and constraint-satisfaction techniques to games and scheduling problems.", "apply", 20),
            ("CO3", "Represent knowledge in propositional and first-order logic and perform inference.", "apply", 20),
            ("CO4", "Apply Bayesian reasoning to problems with uncertainty.", "apply", 15),
            ("CO5", "Explain supervised learning, decision trees and neural-network basics and evaluate simple models.", "evaluate", 20),
        ],
        "co_po": {"CO1": [("PO1", 3), ("PO2", 2)], "CO2": [("PO2", 2), ("PO3", 2)], "CO3": [("PO1", 2)],
                  "CO4": [("PO1", 2), ("PO2", 2)], "CO5": [("PO4", 2), ("PO5", 2)]},
        "topics": [
            ("T-01", "Intelligent agents, environments, rationality"),
            ("T-02", "Problem formulation; BFS, DFS, uniform-cost, iterative deepening"),
            ("T-03", "Heuristics, greedy best-first, A* and admissibility"),
            ("T-04", "Local search: hill climbing, simulated annealing, genetic algorithms"),
            ("T-05", "Adversarial search: minimax, alpha-beta pruning"),
            ("T-06", "Constraint satisfaction: backtracking, arc consistency"),
            ("T-07", "Propositional logic, inference, resolution"),
            ("T-08", "First-order logic, unification, forward/backward chaining"),
            ("T-09", "Probability, Bayes' rule, Bayesian networks"),
            ("T-10", "Supervised learning: decision trees, k-NN, evaluation metrics"),
            ("T-11", "Linear models, gradient descent, perceptron and multilayer networks"),
            ("T-12", "Ethics and societal impact of AI"),
        ],
        "papers": [
            {
                "label": "Final Examination, Spring 2025", "year": 2025, "term": "Spring 2025", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1", "Formulate the 8-puzzle as a search problem (states, actions, transition, goal test, path cost) and compare BFS with iterative deepening in time and space.", 10, "CO1"),
                    ("2", "Apply A* to the given graph using the provided heuristic; show the open list at each step and argue whether the heuristic is admissible and consistent.", 10, "CO1"),
                    ("3", "Apply alpha-beta pruning to the given depth-3 game tree; mark pruned branches and state the minimax value.", 10, "CO2"),
                    ("4(a)", "Convert the sentence 'Every student who studies passes some exam' to first-order logic and clausal form.", 5, "CO3"),
                    ("4(b)", "Use resolution to prove Q from the knowledge base {P → Q, R → Q, P ∨ R}.", 5, "CO3"),
                    ("5", "A test for a disease has 98% sensitivity and 95% specificity; the disease prevalence is 1%. Compute the probability of disease given a positive test and interpret the result.", 10, "CO4"),
                    ("6", "Build the first split of a decision tree for the given dataset using information gain, and explain how you would evaluate the tree using k-fold cross-validation.", 10, "CO5"),
                ],
            },
            {
                "label": "Final Examination, Spring 2026", "year": 2026, "term": "Spring 2026", "declared_total": 60, "is_draft": True,
                "questions": [
                    ("1", "Define a rational agent and PEAS description. Describe the properties of task environments with examples.", 10, None),
                    ("2", "Apply A* to the given graph using the provided heuristic; show the open list at each step and state whether the heuristic is admissible.", 10, None),
                    ("3", "Apply alpha-beta pruning to the given depth-3 game tree; mark the pruned branches and give the minimax value.", 10, None),
                    ("4", "Explain the difference between propositional and first-order logic. Convert 'All birds fly' and 'Tweety is a bird' into first-order logic.", 10, None),
                    ("5", "Describe simulated annealing and genetic algorithms and state one problem where each is preferred.", 10, None),
                    ("6", "Define precision, recall and F1-score. Compute them for the given confusion matrix.", 8, None),
                ],
            },
        ],
        "marks": {"paper": 0, "students": 26, "ability": {"CO1": 0.73, "CO2": 0.66, "CO3": 0.51, "CO4": 0.62, "CO5": 0.70}, "term": "Spring 2025"},
    },
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "farhana.islam@aust.edu",
        "code": "CSE 4105",
        "title": "Machine Learning",
        "term": "Spring 2026",
        "description": "Supervised and unsupervised learning, model selection and evaluation, linear and logistic regression, "
                       "decision trees and ensembles, neural networks, clustering and dimensionality reduction.",
        "outcomes": [
            ("CO1", "Explain the machine-learning workflow, bias-variance trade-off and evaluation metrics.", "understand", 15),
            ("CO2", "Apply linear and logistic regression with gradient descent and regularisation.", "apply", 20),
            ("CO3", "Apply decision trees, random forests and boosting to classification problems.", "apply", 20),
            ("CO4", "Design and train feed-forward neural networks with backpropagation.", "apply", 25),
            ("CO5", "Apply clustering and dimensionality-reduction techniques and interpret the results.", "analyze", 20),
        ],
        "co_po": {"CO1": [("PO1", 2)], "CO2": [("PO1", 2), ("PO2", 2)], "CO3": [("PO2", 2), ("PO3", 2)],
                  "CO4": [("PO3", 3), ("PO5", 2)], "CO5": [("PO2", 2), ("PO4", 2)]},
        "topics": [
            ("T-01", "ML workflow, train/validation/test, cross-validation, metrics"),
            ("T-02", "Bias-variance trade-off, overfitting, regularisation"),
            ("T-03", "Linear regression and gradient descent"),
            ("T-04", "Logistic regression and softmax"),
            ("T-05", "Decision trees, information gain, pruning"),
            ("T-06", "Ensembles: bagging, random forests, boosting"),
            ("T-07", "k-nearest neighbours and support vector machines"),
            ("T-08", "Perceptron, multilayer networks, backpropagation"),
            ("T-09", "Convolutional networks overview"),
            ("T-10", "Clustering: k-means, hierarchical, DBSCAN"),
            ("T-11", "Dimensionality reduction: PCA"),
            ("T-12", "Fairness, interpretability and ethics in ML"),
        ],
        "papers": [
            {
                "label": "Final Examination, Fall 2025", "year": 2025, "term": "Fall 2025", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1", "Explain the bias-variance trade-off and how k-fold cross-validation helps choose model complexity.", 10, "CO1"),
                    ("2", "Derive the gradient-descent update for linear regression with L2 regularisation and perform two iterations on the given data with learning rate 0.1.", 12, "CO2"),
                    ("3", "Compute the information gain of each attribute for the given dataset and construct the first two levels of a decision tree. Explain how a random forest would reduce variance.", 12, "CO3"),
                    ("4", "For a 2-2-1 network with sigmoid units, perform one forward pass and one backpropagation step on the given input and target; show all intermediate values.", 14, "CO4"),
                    ("5", "Run two iterations of k-means (k = 2) on the given 2-D points starting from the given centroids, and explain how PCA could be used to visualise a 10-dimensional dataset.", 12, "CO5"),
                ],
            },
        ],
    },
    # ----------------------------------------------------------------------------------------------------
    {
        "owner": "tanvir.ahmed@aust.edu",
        "code": "CSE 1101",
        "title": "Structured Programming",
        "term": "Spring 2026",
        "description": "Problem solving with C: data types, control flow, functions and recursion, arrays and strings, pointers, "
                       "structures, dynamic memory and file I/O.",
        "outcomes": [
            ("CO1", "Explain the structure of a C program, data types, operators and expression evaluation.", "understand", 15),
            ("CO2", "Apply selection and iteration constructs to solve computational problems.", "apply", 20),
            ("CO3", "Design modular programs using functions and recursion.", "apply", 20),
            ("CO4", "Apply arrays, strings and pointers to manipulate collections of data.", "apply", 25),
            ("CO5", "Use structures, dynamic memory allocation and files to build small data-processing programs.", "apply", 20),
        ],
        "co_po": {"CO1": [("PO1", 2)], "CO2": [("PO1", 2), ("PO2", 2)], "CO3": [("PO3", 2)],
                  "CO4": [("PO1", 2), ("PO3", 2)], "CO5": [("PO3", 2), ("PO5", 2)]},
        "topics": [
            ("T-01", "Algorithms, flowcharts, structure of a C program"),
            ("T-02", "Data types, variables, operators, type conversion"),
            ("T-03", "Input/output with scanf and printf"),
            ("T-04", "if/else, switch, ternary operator"),
            ("T-05", "Loops: for, while, do-while; break and continue"),
            ("T-06", "Functions, scope, parameter passing"),
            ("T-07", "Recursion"),
            ("T-08", "One- and two-dimensional arrays"),
            ("T-09", "Strings and the string library"),
            ("T-10", "Pointers, pointer arithmetic, pointers and arrays"),
            ("T-11", "Structures and unions"),
            ("T-12", "Dynamic memory: malloc, calloc, realloc, free"),
            ("T-13", "File handling"),
        ],
        "papers": [
            {
                "label": "Final Examination, Fall 2025", "year": 2025, "term": "Fall 2025", "declared_total": 60, "is_draft": False,
                "questions": [
                    ("1(a)", "Explain the difference between = and ==, and between the pre-increment and post-increment operators, with the output of short code fragments.", 5, "CO1"),
                    ("1(b)", "Evaluate the expression 7 + 3 * 2 % 4 - 8 / 3 step by step according to C precedence and associativity.", 5, "CO1"),
                    ("2(a)", "Write a C program that reads integers until a negative number is entered and prints the count of even numbers and the sum of odd numbers.", 6, "CO2"),
                    ("2(b)", "Write a program that prints the following pattern for n rows using nested loops (right-aligned triangle of stars).", 4, "CO2"),
                    ("3", "Write a recursive function to compute the n-th Fibonacci number and trace the calls for n = 5. Then write an iterative version and compare their efficiency.", 10, "CO3"),
                    ("4(a)", "Write a function that takes a string and returns 1 if it is a palindrome (ignoring case) and 0 otherwise, without using library string functions.", 6, "CO4"),
                    ("4(b)", "Write a function that receives a 2-D array (n×n) and returns the sum of its two diagonals.", 6, "CO4"),
                    ("5(a)", "Explain pointer arithmetic. Given int a[5] = {2,4,6,8,10}; int *p = a; what are the values of *(p+2), *p+2 and p[4]?", 6, "CO4"),
                    ("5(b)", "Define a structure Student with id, name and cgpa. Write a program that reads n students into a dynamically allocated array and writes those with cgpa ≥ 3.5 to a file.", 12, "CO5"),
                ],
            },
            {
                "label": "Final Examination, Spring 2026", "year": 2026, "term": "Spring 2026", "declared_total": 60, "is_draft": True,
                "questions": [
                    ("1(a)", "List the basic data types in C with their typical sizes. What is the output of printf(\"%d\", 5/2*2.0)?", 5, None),
                    ("1(b)", "Explain the difference between = and ==, and between the pre-increment and post-increment operators, with the output of short code fragments.", 5, None),
                    ("2(a)", "Write a C program that reads integers until zero is entered and prints the largest and smallest values.", 6, None),
                    ("2(b)", "Write a program that prints Floyd's triangle for n rows.", 4, None),
                    ("3", "Write a recursive function to compute the GCD of two integers using Euclid's algorithm and trace it for (48, 18).", 10, None),
                    ("4(a)", "Write a function that counts vowels, consonants and digits in a string.", 5, None),
                    ("4(b)", "Write a function that transposes an n×n matrix in place.", 5, None),
                    ("5", "Write a function that receives a string and returns 1 if it is a palindrome, ignoring case, without using library string functions.", 8, None),
                    ("6", "Given int a[5] = {1,3,5,7,9}; int *p = a + 1; what are *p, *(p+2), p[-1] and *a + 3? Explain each.", 8, None),
                ],
            },
        ],
        "marks": {"paper": 0, "students": 35, "ability": {"CO1": 0.82, "CO2": 0.78, "CO3": 0.61, "CO4": 0.57, "CO5": 0.45}, "term": "Fall 2025"},
        "rubric": {
            "label": "Rubric — Q5(b) Student records with structures and files (12 marks)", "year": 2025, "term": "Fall 2025",
            "question_ref": "5(b)",
            "criteria": [
                ("R1", "Structure definition and dynamic allocation: correct struct Student, malloc/calloc sized by n, NULL check.", 3,
                 [("3", 3, "Correct struct, allocation sized by n, allocation failure checked."), ("2", 2, "Correct struct and allocation, no failure check."),
                  ("1", 1, "Struct or allocation partly wrong."), ("0", 0, "No usable structure or allocation.")]),
                ("R2", "Input handling: reads n records correctly including strings with spaces.", 3,
                 [("3", 3, "All fields read correctly, handles names with spaces."), ("2", 2, "Reads fields but names with spaces break."),
                  ("1", 1, "Partial or incorrect reading."), ("0", 0, "No input logic.")]),
                ("R3", "Filtering and file output: opens file with error check, writes only cgpa ≥ 3.5, closes file.", 4,
                 [("4", 4, "Correct filter, fopen checked, fprintf format sensible, fclose."), ("3", 3, "Correct filter and output, missing fopen check or fclose."),
                  ("2", 2, "Filter wrong boundary or writes all records."), ("1", 1, "File opened but no meaningful output."), ("0", 0, "No file handling.")]),
                ("R4", "Code quality: meaningful names, indentation, frees memory, comments where needed.", 2,
                 [("2", 2, "Clean, consistent, memory freed."), ("1", 1, "Readable but memory not freed or inconsistent style."), ("0", 0, "Hard to read.")]),
            ],
        },
        "answers": {
            "label": "Answer scripts — Q5(b), Fall 2025 (two graders)", "year": 2025, "term": "Fall 2025",
            "graders": ["Grader A", "Grader B"],
            "items": [
                ("S-101", "5(b)",
                 "struct Student { int id; char name[50]; float cgpa; }; In main I read n with scanf then allocate struct Student *s = malloc(n * sizeof *s); if (!s) return 1; "
                 "Loop i from 0 to n-1: scanf(\"%d\", &s[i].id); getchar(); fgets(s[i].name, 50, stdin); strip newline; scanf(\"%f\", &s[i].cgpa). "
                 "FILE *fp = fopen(\"honours.txt\", \"w\"); if (fp == NULL) { printf(\"cannot open\"); return 1; } for each i if (s[i].cgpa >= 3.5) fprintf(fp, \"%d %s %.2f\\n\", ...). fclose(fp); free(s); return 0.",
                 {"Grader A": {"R1": 3, "R2": 3, "R3": 4, "R4": 2}, "Grader B": {"R1": 3, "R2": 3, "R3": 4, "R4": 2}}),
                ("S-102", "5(b)",
                 "struct Student {int id; char name[30]; float cgpa;}; struct Student s[100]; scanf n; for i: scanf(\"%d %s %f\", &s[i].id, s[i].name, &s[i].cgpa); "
                 "FILE *f = fopen(\"out.txt\",\"w\"); for i: if (s[i].cgpa > 3.5) fprintf(f, \"%d %s %f\", s[i].id, s[i].name, s[i].cgpa); fclose(f);",
                 {"Grader A": {"R1": 1, "R2": 2, "R3": 2, "R4": 1}, "Grader B": {"R1": 2, "R2": 2, "R3": 3, "R4": 1}}),
                ("S-103", "5(b)",
                 "I define struct Student with id, name[40], cgpa. Read n. struct Student *arr = (struct Student*)calloc(n, sizeof(struct Student)); "
                 "for i: scanf(\"%d\", &arr[i].id); scanf(\" %[^\\n]\", arr[i].name); scanf(\"%f\", &arr[i].cgpa); "
                 "FILE *fp = fopen(\"result.txt\", \"w\"); for i: if (arr[i].cgpa >= 3.5) fprintf(fp, \"%d,%s,%.2f\\n\", arr[i].id, arr[i].name, arr[i].cgpa); fclose(fp); free(arr);",
                 {"Grader A": {"R1": 2, "R2": 3, "R3": 3, "R4": 2}, "Grader B": {"R1": 3, "R2": 3, "R3": 4, "R4": 2}}),
                ("S-104", "5(b)",
                 "struct student {int id; char name[20]; float cgpa;} st; scanf(\"%d\", &n); for (i=0;i<n;i++) { scanf(\"%d%s%f\", &st.id, st.name, &st.cgpa); if (st.cgpa >= 3.5) printf(\"%d %s\\n\", st.id, st.name); }",
                 {"Grader A": {"R1": 0, "R2": 1, "R3": 0, "R4": 1}, "Grader B": {"R1": 1, "R2": 2, "R3": 2, "R4": 1}}),
                ("S-105", "5(b)",
                 "typedef struct { int id; char name[50]; double cgpa; } Student; Student *list = malloc(sizeof(Student) * n); no NULL check. Read each with scanf(\"%d %49s %lf\"). "
                 "FILE *out = fopen(\"top.txt\", \"w\"); if (!out) { perror(\"fopen\"); free(list); return 1; } for each: if (list[i].cgpa >= 3.5) fprintf(out, \"%d\\t%s\\t%.2lf\\n\", ...); fclose(out); free(list);",
                 {"Grader A": {"R1": 2, "R2": 2, "R3": 4, "R4": 2}, "Grader B": {"R1": 2, "R2": 2, "R3": 4, "R4": 2}}),
                ("S-106", "5(b)",
                 "struct Student { int id; char name[50]; float cgpa; }; struct Student *s = malloc(n * sizeof(struct Student)); read with a loop using scanf for id and cgpa and gets for name. "
                 "Then: FILE *fp; fp = fopen(\"file.txt\", \"r\"); for i if cgpa >= 3.5 fprintf(fp, ...). Did not close file or free memory.",
                 {"Grader A": {"R1": 2, "R2": 2, "R3": 1, "R4": 0}, "Grader B": {"R1": 2, "R2": 2, "R3": 3, "R4": 1}}),
            ],
        },
    },
]


def syllabus_text(course: dict) -> str:
    lines = [
        f"{course['code']} {course['title']}",
        "Ahsanullah University of Science and Technology — Department of Computer Science and Engineering",
        f"Session: {course['term']}",
        "",
        "Course description",
        course["description"],
        "",
        "Course outcomes",
    ]
    for code, text, _bloom, weight in course["outcomes"]:
        lines.append(f"{code}: {text} (weight {weight}%)")
    lines += ["", "Weekly topics"]
    for i, (_code, title) in enumerate(course["topics"], start=1):
        lines.append(f"Week {i}: {title}")
    lines += ["", "Assessment: attendance 10%, quizzes 20%, mid-term 20%, final examination 50%."]
    return "\n".join(lines)


def paper_text(paper: dict) -> str:
    lines = [paper["label"], f"Total marks: {paper['declared_total']}", "Answer all questions.", ""]
    for number, text, marks, _co in paper["questions"]:
        lines.append(f"{number} {text} [{marks}]")
    return "\n".join(lines)
