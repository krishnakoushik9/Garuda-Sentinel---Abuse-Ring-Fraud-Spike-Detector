package com.boi.launcher;

import com.formdev.flatlaf.FlatDarkLaf;

import javax.swing.*;
import javax.swing.border.Border;
import javax.swing.border.EmptyBorder;
import javax.swing.text.*;
import java.awt.*;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.Socket;
import java.net.URI;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.List;
import java.util.concurrent.*;

public class GarudaSentinelLauncher extends JFrame {

    // Theme Custom Colors
    private static final Color COLOR_BG_DARK = new Color(18, 18, 18);
    private static final Color COLOR_PANEL_DARK = new Color(30, 30, 30);
    private static final Color COLOR_CARD_DARK = new Color(37, 37, 38);
    private static final Color COLOR_BORDER_DARK = new Color(55, 55, 57);
    
    private static final Color COLOR_TEXT_MUTED = new Color(150, 150, 150);
    private static final Color COLOR_CYAN = new Color(0, 229, 255);
    private static final Color COLOR_AMBER = new Color(255, 171, 0);
    private static final Color COLOR_RED = new Color(255, 23, 68);
    private static final Color COLOR_GREEN = new Color(0, 230, 118);
    private static final Color COLOR_BLUE = new Color(33, 150, 243);
    
    // Subsystem States
    public enum ServiceStatus {
        OFFLINE(COLOR_RED, "OFFLINE"),
        STARTING(COLOR_AMBER, "STARTING"),
        ONLINE(COLOR_GREEN, "ONLINE");

        final Color color;
        final String text;

        ServiceStatus(Color color, String text) {
            this.color = color;
            this.text = text;
        }
    }

    // Services
    private enum ServiceName {
        FRONTEND("React Frontend", "Port 5173 (Vite)", "http://localhost:5173"),
        BACKEND("FastAPI Backend", "Port 8000 (Uvicorn)", "http://localhost:8000/"),
        AI_MODELS("AI Models Layer", "XGBoost, GNN, LSTM", "models/xgb_fraud.json"),
        NEO4J("Neo4j Database", "Port 7687 (Bolt)", "localhost:7687"),
        REDIS("Redis Watchlist", "Port 6379 (Cache)", "localhost:6379"),
        KAFKA("Kafka Event Broker", "Port 9092 (Streams)", "localhost:9092"),
        COBOL("COBOL", "Continuous Engine", "database/ecosystem.db");

        final String label;
        final String details;
        final String address;

        ServiceName(String label, String details, String address) {
            this.label = label;
            this.details = details;
            this.address = address;
        }
    }

    private final Map<ServiceName, ServiceStatus> statusMap = new ConcurrentHashMap<>();
    private final Map<ServiceName, JPanel> statusCardMap = new HashMap<>();
    private final Map<ServiceName, JLabel> statusLabelMap = new HashMap<>();
    private final Map<ServiceName, JLabel> indicatorDotMap = new HashMap<>();
    private final Map<ServiceName, JButton> startBtnMap = new HashMap<>();
    private final Map<ServiceName, JButton> stopBtnMap = new HashMap<>();
    private volatile String customAccounts = null;
    private volatile String customTransactions = null;
    private volatile String customSpeed = null;
    private volatile boolean manualDummyOnline = false;

    private static final Color COLOR_GREEN_DARK = new Color(0, 150, 70);
    private static final Color COLOR_RED_DARK = new Color(180, 10, 40);

    // Process Handles
    private final Map<String, Process> activeProcesses = new ConcurrentHashMap<>();
    private final ExecutorService logReadingExecutor = Executors.newCachedThreadPool();
    private ScheduledExecutorService healthCheckExecutor;
    
    // UI Elements
    private JButton btnStart;
    private JButton btnStop;
    private JButton btnOpenDashboard;
    private JTextPane consolePane;
    private StyledDocument consoleDoc;
    private JCheckBox chkShowBackend;
    private JCheckBox chkShowFrontend;
    private JCheckBox chkShowSim;
    private JCheckBox chkShowSystem;
    private JProgressBar swapProgressBar;
    private JLabel lblSwapStats;
    private JLabel lblProtectedCount;

    // Docker Compose availability flags
    private volatile boolean isDockerComposeAvailable = false;
    private volatile boolean isLegacyDockerComposeAvailable = false;

    // Working directory path
    private final String workspaceRoot;

    public GarudaSentinelLauncher() {
        // Resolve Workspace Root Directory robustly relative to the executing binary or JAR location
        String resolvedRoot = null;
        try {
            String pathStr = GarudaSentinelLauncher.class.getProtectionDomain().getCodeSource().getLocation().toURI().getPath();
            if (pathStr != null && !pathStr.isEmpty()) {
                File pathFile = new File(pathStr);
                if (pathFile.isFile()) {
                    pathFile = pathFile.getParentFile();
                }
                
                if (pathFile != null) {
                    if (pathFile.getName().equals("target")) {
                        File parent = pathFile.getParentFile(); // launcher
                        if (parent != null && parent.getName().equals("launcher")) {
                            resolvedRoot = parent.getParentFile().getAbsolutePath();
                        } else {
                            resolvedRoot = parent.getAbsolutePath();
                        }
                    } else if (pathFile.getName().equals("launcher")) {
                        resolvedRoot = pathFile.getParentFile().getAbsolutePath();
                    } else {
                        resolvedRoot = pathFile.getAbsolutePath();
                    }
                }
            }
        } catch (Exception ex) {
            // Fallback if URI parsing fails
        }

        if (resolvedRoot == null) {
            String currentDir = System.getProperty("user.dir");
            Path path = Paths.get(currentDir);
            if (path.getFileName().toString().equals("launcher")) {
                resolvedRoot = path.getParent().toAbsolutePath().toString();
            } else {
                resolvedRoot = path.toAbsolutePath().toString();
            }
        }
        workspaceRoot = resolvedRoot;

        // Initialize Services to OFFLINE
        for (ServiceName service : ServiceName.values()) {
            statusMap.put(service, ServiceStatus.OFFLINE);
        }

        setupUI();
        startHealthCheckScheduler();
        
        log(Color.WHITE, "========================================================================\n", true);
        log(COLOR_CYAN, "  BOI GARUDA SENTINEL — Master Launcher Initialized\n", true);
        log(COLOR_TEXT_MUTED, "  Workspace Root: " + workspaceRoot + "\n", false);
        log(Color.WHITE, "========================================================================\n", true);

        verifyPrerequisitesAsync();
    }

    private void setupUI() {
        setTitle("BOI GARUDA SENTINEL — Operations & Intelligence Control Panel");
        setSize(1650, 1050);
        setMinimumSize(new Dimension(1300, 850));
        setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE);
        setLocationRelativeTo(null);
        getContentPane().setBackground(COLOR_BG_DARK);

        // Standard window close handling
        addWindowListener(new WindowAdapter() {
            @Override
            public void windowClosing(WindowEvent e) {
                handleExit();
            }
        });

        // Custom Layout
        setLayout(new BorderLayout());

        // 1. TOP HEADER SECTION
        JPanel headerPanel = new JPanel(new BorderLayout());
        headerPanel.setBackground(COLOR_PANEL_DARK);
        headerPanel.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(0, 0, 1, 0, COLOR_BORDER_DARK),
                new EmptyBorder(15, 20, 15, 20)
        ));

        JPanel titleContainer = new JPanel(new GridLayout(2, 1, 2, 2));
        titleContainer.setOpaque(false);
        
        JLabel lblTitle = new JLabel("BOI GARUDA SENTINEL");
        lblTitle.setFont(new Font("SansSerif", Font.BOLD, 42));
        lblTitle.setForeground(COLOR_CYAN);
        
        JLabel lblSubtitle = new JLabel("Fraud Intelligence Platform • Modern Legacy CBS Orchestrator");
        lblSubtitle.setFont(new Font("SansSerif", Font.PLAIN, 20));
        lblSubtitle.setForeground(COLOR_TEXT_MUTED);

        titleContainer.add(lblTitle);
        titleContainer.add(lblSubtitle);
        headerPanel.add(titleContainer, BorderLayout.WEST);

        // Mini Brand Info
        JLabel lblVersion = new JLabel("FDS v5.0 [Active Mode]");
        lblVersion.setFont(new Font("Monospaced", Font.BOLD, 20));
        lblVersion.setForeground(COLOR_AMBER);
        headerPanel.add(lblVersion, BorderLayout.EAST);

        add(headerPanel, BorderLayout.NORTH);

        // 2. MIDDLE DASHBOARD SECTION
        JPanel mainContentPanel = new JPanel(new GridBagLayout());
        mainContentPanel.setOpaque(false);
        mainContentPanel.setBorder(new EmptyBorder(15, 15, 15, 15));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.BOTH;
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.weightx = 1.0;
        gbc.weighty = 0.35; // 35% height for grid status cards
        gbc.insets = new Insets(0, 0, 15, 0);

        // Dashboard Status Cards Panel (FlowLayout or Grid)
        JPanel statusGridPanel = new JPanel(new GridLayout(2, 4, 22, 22));
        statusGridPanel.setOpaque(false);

        for (ServiceName service : ServiceName.values()) {
            JPanel card = createStatusCard(service);
            statusGridPanel.add(card);
            statusCardMap.put(service, card);
        }
        
        // Add an extra panel for platform quick summary stats
        JPanel summaryCard = createSummaryCard();
        statusGridPanel.add(summaryCard);

        mainContentPanel.add(statusGridPanel, gbc);

        // 3. BOTTOM SECTION - LOG CONSOLE & CONTROLS
        gbc.gridy = 1;
        gbc.weighty = 0.65; // 65% height for log area & buttons
        gbc.insets = new Insets(0, 0, 0, 0);

        JPanel bottomWrapperPanel = new JPanel(new BorderLayout());
        bottomWrapperPanel.setOpaque(false);

        // 3.1 Log Console Area
        JPanel consolePanelWrapper = new JPanel(new BorderLayout());
        consolePanelWrapper.setBackground(COLOR_PANEL_DARK);
        consolePanelWrapper.setBorder(BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1, true));

        // Console Header with Filter Options
        JPanel consoleHeaderPanel = new JPanel(new BorderLayout());
        consoleHeaderPanel.setBackground(COLOR_PANEL_DARK);
        consoleHeaderPanel.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(0, 0, 1, 0, COLOR_BORDER_DARK),
                new EmptyBorder(8, 12, 8, 12)
        ));

        JLabel lblConsole = new JLabel("LIVE INTELLIGENCE STREAM & DIAGNOSTIC SYSTEM LOGS");
        lblConsole.setFont(new Font("SansSerif", Font.BOLD, 18));
        lblConsole.setForeground(COLOR_TEXT_MUTED);
        consoleHeaderPanel.add(lblConsole, BorderLayout.WEST);

        // Filter Checkboxes
        JPanel filterPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 15, 0));
        filterPanel.setOpaque(false);

        chkShowSystem = new JCheckBox("Launcher", true);
        chkShowBackend = new JCheckBox("Backend", true);
        chkShowFrontend = new JCheckBox("Frontend", true);
        chkShowSim = new JCheckBox("Simulation", true);

        // Apply dark styled checkboxes
        styleCheckbox(chkShowSystem);
        styleCheckbox(chkShowBackend);
        styleCheckbox(chkShowFrontend);
        styleCheckbox(chkShowSim);

        filterPanel.add(chkShowSystem);
        filterPanel.add(chkShowBackend);
        filterPanel.add(chkShowFrontend);
        filterPanel.add(chkShowSim);
        consoleHeaderPanel.add(filterPanel, BorderLayout.EAST);

        consolePanelWrapper.add(consoleHeaderPanel, BorderLayout.NORTH);

        // Monospaced text pane for log console
        consolePane = new JTextPane();
        consolePane.setEditable(false);
        consolePane.setBackground(COLOR_BG_DARK);
        consolePane.setFont(new Font("Monospaced", Font.PLAIN, 20));
        consoleDoc = consolePane.getStyledDocument();

        JScrollPane scrollPane = new JScrollPane(consolePane);
        scrollPane.setBorder(null);
        scrollPane.getVerticalScrollBar().setUnitIncrement(12);
        consolePanelWrapper.add(scrollPane, BorderLayout.CENTER);

        // Console Action Buttons (Clear, Export)
        JPanel consoleActionPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 10, 5));
        consoleActionPanel.setBackground(COLOR_PANEL_DARK);
        consoleActionPanel.setBorder(BorderFactory.createMatteBorder(1, 0, 0, 0, COLOR_BORDER_DARK));

        JButton btnClear = new JButton("Clear Console");
        styleConsoleButton(btnClear);
        btnClear.addActionListener(e -> consolePane.setText(""));

        JButton btnCopy = new JButton("Copy All");
        styleConsoleButton(btnCopy);
        btnCopy.addActionListener(e -> {
            consolePane.selectAll();
            consolePane.copy();
            consolePane.setCaretPosition(consoleDoc.getLength());
            JOptionPane.showMessageDialog(this, "Logs copied to clipboard.", "Info", JOptionPane.INFORMATION_MESSAGE);
        });

        consoleActionPanel.add(btnClear);
        consoleActionPanel.add(btnCopy);
        consolePanelWrapper.add(consoleActionPanel, BorderLayout.SOUTH);

        bottomWrapperPanel.add(consolePanelWrapper, BorderLayout.CENTER);

        // 3.2 Action Toolbar Controls (START, STOP, OPEN DASHBOARD)
        JPanel toolbarPanel = new JPanel(new FlowLayout(FlowLayout.CENTER, 25, 12));
        toolbarPanel.setOpaque(false);

        btnStart = new JButton("START PLATFORM");
        btnStart.setFont(new Font("SansSerif", Font.BOLD, 24));
        btnStart.setForeground(Color.BLACK);
        btnStart.setBackground(COLOR_GREEN);
        btnStart.setPreferredSize(new Dimension(380, 80));
        btnStart.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnStart.addActionListener(e -> triggerStartSequence());

        btnStop = new JButton("SHUTDOWN SERVICES");
        btnStop.setFont(new Font("SansSerif", Font.BOLD, 24));
        btnStop.setForeground(Color.WHITE);
        btnStop.setBackground(COLOR_RED);
        btnStop.setPreferredSize(new Dimension(380, 80));
        btnStop.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnStop.setEnabled(false);
        btnStop.addActionListener(e -> triggerShutdownSequence());

        btnOpenDashboard = new JButton("OPEN ANALYST PORTAL");
        btnOpenDashboard.setFont(new Font("SansSerif", Font.BOLD, 24));
        btnOpenDashboard.setForeground(Color.WHITE);
        btnOpenDashboard.setBackground(COLOR_BLUE);
        btnOpenDashboard.setPreferredSize(new Dimension(380, 80));
        btnOpenDashboard.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnOpenDashboard.setEnabled(false);
        btnOpenDashboard.addActionListener(e -> openBrowserPortal());

        toolbarPanel.add(btnStart);
        toolbarPanel.add(btnStop);
        toolbarPanel.add(btnOpenDashboard);

        bottomWrapperPanel.add(toolbarPanel, BorderLayout.SOUTH);

        mainContentPanel.add(bottomWrapperPanel, gbc);

        add(mainContentPanel, BorderLayout.CENTER);
    }

    private void styleCheckbox(JCheckBox chk) {
        chk.setOpaque(false);
        chk.setForeground(COLOR_TEXT_MUTED);
        chk.setFont(new Font("SansSerif", Font.BOLD, 18));
        chk.setCursor(new Cursor(Cursor.HAND_CURSOR));
    }

    private void styleConsoleButton(JButton btn) {
        btn.setFont(new Font("SansSerif", Font.BOLD, 16));
        btn.setBackground(COLOR_CARD_DARK);
        btn.setForeground(Color.WHITE);
        btn.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1),
                new EmptyBorder(8, 14, 8, 14)
        ));
        btn.setCursor(new Cursor(Cursor.HAND_CURSOR));
    }

    private JPanel createStatusCard(ServiceName service) {
        JPanel card = new JPanel(new BorderLayout(8, 8));
        card.setBackground(COLOR_CARD_DARK);
        card.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1, true),
                new EmptyBorder(16, 20, 16, 20)
        ));

        // Subsystem Title & Details
        JPanel textPanel = new JPanel(new GridLayout(2, 1, 2, 2));
        textPanel.setOpaque(false);

        JLabel lblTitle = new JLabel(service.label);
        lblTitle.setFont(new Font("SansSerif", Font.BOLD, 24));
        lblTitle.setForeground(Color.WHITE);

        JLabel lblDetail = new JLabel(service.details);
        lblDetail.setFont(new Font("SansSerif", Font.PLAIN, 18));
        lblDetail.setForeground(COLOR_TEXT_MUTED);

        textPanel.add(lblTitle);
        textPanel.add(lblDetail);
        card.add(textPanel, BorderLayout.CENTER);

        // Status Indicator Container
        JPanel indicatorPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 6, 0));
        indicatorPanel.setOpaque(false);

        JLabel dot = new JLabel("●");
        dot.setFont(new Font("SansSerif", Font.BOLD, 32));
        dot.setForeground(COLOR_RED);
        indicatorDotMap.put(service, dot);

        JLabel statusLbl = new JLabel("OFFLINE");
        statusLbl.setFont(new Font("Monospaced", Font.BOLD, 20));
        statusLbl.setForeground(COLOR_RED);
        statusLabelMap.put(service, statusLbl);

        indicatorPanel.add(dot);
        indicatorPanel.add(statusLbl);
        card.add(indicatorPanel, BorderLayout.EAST);

        // Small control buttons at the bottom of each card
        JPanel controlPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 4));
        controlPanel.setOpaque(false);

        JButton btnCardStart = new JButton("▶ Start");
        btnCardStart.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnCardStart.setBackground(COLOR_GREEN_DARK);
        btnCardStart.setForeground(Color.WHITE);
        btnCardStart.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnCardStart.setPreferredSize(new Dimension(110, 32));
        btnCardStart.addActionListener(e -> triggerServiceStart(service));

        JButton btnCardStop = new JButton("■ Stop");
        btnCardStop.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnCardStop.setBackground(COLOR_RED_DARK);
        btnCardStop.setForeground(Color.WHITE);
        btnCardStop.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnCardStop.setPreferredSize(new Dimension(110, 32));
        btnCardStop.setEnabled(false);
        btnCardStop.addActionListener(e -> triggerServiceStop(service));

        controlPanel.add(btnCardStart);
        controlPanel.add(btnCardStop);
        card.add(controlPanel, BorderLayout.SOUTH);

        startBtnMap.put(service, btnCardStart);
        stopBtnMap.put(service, btnCardStop);

        return card;
    }

    private JPanel createSummaryCard() {
        JPanel card = new JPanel(new BorderLayout(8, 8));
        card.setBackground(COLOR_CARD_DARK);
        card.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1, true),
                new EmptyBorder(16, 20, 16, 20)
        ));

        // Header Panel
        JPanel headerPanel = new JPanel(new GridLayout(2, 1, 2, 2));
        headerPanel.setOpaque(false);

        JLabel lblTitle = new JLabel("SWAP & RAM PROTECTION");
        lblTitle.setFont(new Font("SansSerif", Font.BOLD, 22));
        lblTitle.setForeground(COLOR_CYAN);

        lblSwapStats = new JLabel("Swap Used: Loading...");
        lblSwapStats.setFont(new Font("SansSerif", Font.PLAIN, 16));
        lblSwapStats.setForeground(COLOR_TEXT_MUTED);

        headerPanel.add(lblTitle);
        headerPanel.add(lblSwapStats);
        card.add(headerPanel, BorderLayout.NORTH);

        // Center Panel with progress bar and protected PID label
        JPanel centerPanel = new JPanel(new GridLayout(2, 1, 4, 4));
        centerPanel.setOpaque(false);

        swapProgressBar = new JProgressBar(0, 100);
        swapProgressBar.setStringPainted(true);
        swapProgressBar.setFont(new Font("Monospaced", Font.BOLD, 14));
        swapProgressBar.setForeground(COLOR_BLUE);
        swapProgressBar.setBackground(COLOR_PANEL_DARK);
        swapProgressBar.setBorder(BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1));

        lblProtectedCount = new JLabel("Protected Processes: 0 active");
        lblProtectedCount.setFont(new Font("SansSerif", Font.BOLD, 14));
        lblProtectedCount.setForeground(COLOR_AMBER);

        centerPanel.add(swapProgressBar);
        centerPanel.add(lblProtectedCount);
        card.add(centerPanel, BorderLayout.CENTER);

        // South Panel with Action Buttons
        JPanel actionPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 4));
        actionPanel.setOpaque(false);

        JButton btnFlush = new JButton("⚡ Evict to Swap");
        btnFlush.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnFlush.setBackground(COLOR_GREEN_DARK);
        btnFlush.setForeground(Color.WHITE);
        btnFlush.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnFlush.setPreferredSize(new Dimension(135, 32));
        btnFlush.addActionListener(e -> triggerManualSwapFlush());

        JButton btnClean = new JButton("🧹 Clean Cache");
        btnClean.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnClean.setBackground(COLOR_BLUE);
        btnClean.setForeground(Color.WHITE);
        btnClean.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnClean.setPreferredSize(new Dimension(130, 32));
        btnClean.addActionListener(e -> triggerManualCacheClean());

        JButton btnInspect = new JButton("🔍 Inspect");
        btnInspect.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnInspect.setBackground(COLOR_CARD_DARK);
        btnInspect.setForeground(Color.WHITE);
        btnInspect.setBorder(BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1));
        btnInspect.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnInspect.setPreferredSize(new Dimension(100, 32));
        btnInspect.addActionListener(e -> openSwapInspectDialog());

        actionPanel.add(btnFlush);
        actionPanel.add(btnClean);
        actionPanel.add(btnInspect);
        card.add(actionPanel, BorderLayout.SOUTH);

        return card;
    }

    // Update individual service status in UI
    private void updateServiceStatusUI(ServiceName service, ServiceStatus status) {
        statusMap.put(service, status);
        SwingUtilities.invokeLater(() -> {
            JLabel dot = indicatorDotMap.get(service);
            JLabel label = statusLabelMap.get(service);
            JPanel card = statusCardMap.get(service);

            if (dot != null && label != null) {
                dot.setForeground(status.color);
                label.setText(status.text);
                label.setForeground(status.color);
            }

            // Enable/disable individual start/stop buttons based on state
            JButton startBtn = startBtnMap.get(service);
            JButton stopBtn = stopBtnMap.get(service);
            if (startBtn != null && stopBtn != null) {
                if (status == ServiceStatus.ONLINE) {
                    startBtn.setEnabled(false);
                    stopBtn.setEnabled(true);
                } else if (status == ServiceStatus.OFFLINE) {
                    startBtn.setEnabled(true);
                    stopBtn.setEnabled(false);
                } else if (status == ServiceStatus.STARTING) {
                    startBtn.setEnabled(false);
                    stopBtn.setEnabled(false);
                }
            }
        });
    }

    private void executeCommandAsync(String taskName, String[] cmd, String dir) {
        logReadingExecutor.submit(() -> {
            executeCommandBlocking(taskName, cmd, dir);
        });
    }

    private void stopChildProcess(String name) {
        Process p = activeProcesses.remove(name);
        if (p != null && p.isAlive()) {
            try {
                p.descendants().forEach(ph -> {
                    try {
                        ph.destroy();
                    } catch (Exception e) {}
                });
                p.destroy();
                p.waitFor(2, TimeUnit.SECONDS);
                if (p.isAlive()) {
                    p.descendants().forEach(ph -> {
                        try {
                            ph.destroyForcibly();
                        } catch (Exception e) {}
                    });
                    p.destroyForcibly();
                }
            } catch (Exception ex) {
                ex.printStackTrace();
            }
        }
    }

    private void triggerServiceStart(ServiceName service) {
        switch (service) {
            case FRONTEND:
                logSystem("[FRONTEND] Spawning React / Vite development server...");
                updateServiceStatusUI(ServiceName.FRONTEND, ServiceStatus.STARTING);
                
                // Let's run npm install if node_modules don't exist
                Path nodeModulesPath = Paths.get(workspaceRoot, "frontend-react", "node_modules");
                if (!Files.exists(nodeModulesPath)) {
                    logSystem("Running npm install in React directory (first-time boot)...");
                    logReadingExecutor.submit(() -> {
                        boolean ok = executeCommandBlocking("NPM Install", new String[]{"npm", "install"}, workspaceRoot + "/frontend-react");
                        if (ok) {
                            startChildProcess("frontend", new String[]{"npm", "run", "dev"}, workspaceRoot + "/frontend-react", this::logFrontend);
                        } else {
                            log(COLOR_RED, "[FRONTEND] npm install failed. Cannot start React frontend.\n", true);
                            updateServiceStatusUI(ServiceName.FRONTEND, ServiceStatus.OFFLINE);
                        }
                    });
                } else {
                    startChildProcess("frontend", new String[]{"npm", "run", "dev"}, workspaceRoot + "/frontend-react", this::logFrontend);
                }
                break;

            case BACKEND:
                logSystem("[BACKEND] Spawning FastAPI server at localhost:8000...");
                updateServiceStatusUI(ServiceName.BACKEND, ServiceStatus.STARTING);
                Path venvPath = Paths.get(workspaceRoot, ".venv");
                String pythonBin = "python3";
                if (Files.exists(venvPath)) {
                    pythonBin = venvPath.resolve("bin").resolve("python3").toString();
                }
                startChildProcess("backend", new String[]{pythonBin, "src/api/main.py"}, workspaceRoot, this::logBackend);
                break;

            case AI_MODELS:
                logSystem("[AI MODELS] Starting AI model training pipeline...");
                Path venvPathAI = Paths.get(workspaceRoot, ".venv");
                String pythonBinAI = "python3";
                if (Files.exists(venvPathAI)) {
                    pythonBinAI = venvPathAI.resolve("bin").resolve("python3").toString();
                }
                startChildProcess("ai_training", new String[]{pythonBinAI, "scripts/train_models.py"}, workspaceRoot, this::logBackend);
                break;

            case NEO4J:
                logSystem("[NEO4J] Booting up Neo4j Graph Database...");
                updateServiceStatusUI(ServiceName.NEO4J, ServiceStatus.STARTING);
                bootDockerService("neo4j");
                break;

            case REDIS:
                logSystem("[REDIS] Booting up Redis Key-Value Watchlist Cache...");
                updateServiceStatusUI(ServiceName.REDIS, ServiceStatus.STARTING);
                bootDockerService("redis");
                break;

            case KAFKA:
                logSystem("[KAFKA] Booting up Kafka Event Broker...");
                updateServiceStatusUI(ServiceName.KAFKA, ServiceStatus.STARTING);
                bootDockerService("kafka");
                break;

            case COBOL:
                openCobolRunnerDialog();
                break;
        }
    }

    private void triggerServiceStop(ServiceName service) {
        switch (service) {
            case FRONTEND:
                logSystem("[FRONTEND] Shutting down Vite server...");
                stopChildProcess("frontend");
                freePort(5173);
                updateServiceStatusUI(ServiceName.FRONTEND, ServiceStatus.OFFLINE);
                break;

            case BACKEND:
                logSystem("[BACKEND] Shutting down FastAPI server...");
                stopChildProcess("backend");
                freePort(8000);
                updateServiceStatusUI(ServiceName.BACKEND, ServiceStatus.OFFLINE);
                break;

            case AI_MODELS:
                logSystem("[AI MODELS] Stopping model training process...");
                stopChildProcess("ai_training");
                break;

            case NEO4J:
                logSystem("[NEO4J] Stopping Neo4j container...");
                shutdownDockerService("neo4j");
                break;

            case REDIS:
                logSystem("[REDIS] Stopping Redis container...");
                shutdownDockerService("redis");
                break;

            case KAFKA:
                logSystem("[KAFKA] Stopping Kafka container...");
                shutdownDockerService("kafka");
                break;

            case COBOL:
                logSystem("[COBOL] Deactivating simulation feeds...");
                manualDummyOnline = false;
                Path stopFile = Paths.get(workspaceRoot, "runtime", "guard.stop");
                try {
                    Files.writeString(stopFile, "stop");
                } catch (Exception ex) {}
                stopChildProcess("simulator");
                updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.OFFLINE);
                break;
        }
    }

    private String[] getDatabaseStats() {
        String[] stats = {"0", "0"};
        try {
            Path dbPath = Paths.get(workspaceRoot, "database", "ecosystem.db");
            if (Files.exists(dbPath)) {
                Process p1 = Runtime.getRuntime().exec(new String[]{"sqlite3", dbPath.toString(), "SELECT count(*) FROM accounts"});
                BufferedReader r1 = new BufferedReader(new InputStreamReader(p1.getInputStream()));
                String line1 = r1.readLine();
                if (line1 != null) stats[0] = String.format("%,d", Integer.parseInt(line1.trim()));
                
                Process p2 = Runtime.getRuntime().exec(new String[]{"sqlite3", dbPath.toString(), "SELECT count(*) FROM transactions"});
                BufferedReader r2 = new BufferedReader(new InputStreamReader(p2.getInputStream()));
                String line2 = r2.readLine();
                if (line2 != null) stats[1] = String.format("%,d", Integer.parseInt(line2.trim()));
            }
        } catch (Exception e) {
            stats[0] = "Unavailable";
            stats[1] = "Unavailable";
        }
        return stats;
    }

    private void openCobolRunnerDialog() {
        JDialog dialog = new JDialog(this, "COBOL Core Engine Configurator", true);
        dialog.setSize(600, 520);
        dialog.setLocationRelativeTo(this);
        dialog.getContentPane().setBackground(COLOR_BG_DARK);
        dialog.setLayout(new BorderLayout(15, 15));
        ((JComponent)dialog.getContentPane()).setBorder(new EmptyBorder(20, 20, 20, 20));

        // Header Panel
        JPanel headerPanel = new JPanel(new GridLayout(2, 1, 2, 2));
        headerPanel.setOpaque(false);
        JLabel lblTitle = new JLabel("COBOL CORE ENGINE CONFIGURATOR");
        lblTitle.setFont(new Font("SansSerif", Font.BOLD, 22));
        lblTitle.setForeground(COLOR_CYAN);
        JLabel lblSub = new JLabel("Manage legacy CBS files, generator velocities, and data schemas");
        lblSub.setFont(new Font("SansSerif", Font.PLAIN, 14));
        lblSub.setForeground(COLOR_TEXT_MUTED);
        headerPanel.add(lblTitle);
        headerPanel.add(lblSub);
        dialog.add(headerPanel, BorderLayout.NORTH);

        // Center Content Panel
        JPanel centerPanel = new JPanel(new GridBagLayout());
        centerPanel.setOpaque(false);
        GridBagConstraints g = new GridBagConstraints();
        g.fill = GridBagConstraints.HORIZONTAL;
        g.insets = new Insets(8, 8, 8, 8);
        g.weightx = 1.0;

        // 1. Current Database Stats Box
        g.gridx = 0;
        g.gridy = 0;
        g.gridwidth = 2;
        JPanel statsPanel = new JPanel(new GridLayout(1, 2, 10, 10));
        statsPanel.setBackground(COLOR_PANEL_DARK);
        statsPanel.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1, true),
                new EmptyBorder(12, 16, 12, 16)
        ));

        String[] dbStats = getDatabaseStats();

        JPanel pAcc = new JPanel(new BorderLayout());
        pAcc.setOpaque(false);
        JLabel lAccTitle = new JLabel("EXISTING ACCOUNTS");
        lAccTitle.setFont(new Font("SansSerif", Font.BOLD, 12));
        lAccTitle.setForeground(COLOR_TEXT_MUTED);
        JLabel lAccVal = new JLabel(dbStats[0]);
        lAccVal.setFont(new Font("Monospaced", Font.BOLD, 20));
        lAccVal.setForeground(COLOR_AMBER);
        pAcc.add(lAccTitle, BorderLayout.NORTH);
        pAcc.add(lAccVal, BorderLayout.CENTER);

        JPanel pTxn = new JPanel(new BorderLayout());
        pTxn.setOpaque(false);
        JLabel lTxnTitle = new JLabel("EXISTING TRANSACTIONS");
        lTxnTitle.setFont(new Font("SansSerif", Font.BOLD, 12));
        lTxnTitle.setForeground(COLOR_TEXT_MUTED);
        JLabel lTxnVal = new JLabel(dbStats[1]);
        lTxnVal.setFont(new Font("Monospaced", Font.BOLD, 20));
        lTxnVal.setForeground(COLOR_AMBER);
        pTxn.add(lTxnTitle, BorderLayout.NORTH);
        pTxn.add(lTxnVal, BorderLayout.CENTER);

        statsPanel.add(pAcc);
        statsPanel.add(pTxn);
        centerPanel.add(statsPanel, g);

        // 2. Input Fields
        g.gridwidth = 1;
        
        // Target Accounts Label & Field
        g.gridy = 1; g.gridx = 0;
        JLabel lblAcc = new JLabel("Target Accounts (Total Limit):");
        lblAcc.setFont(new Font("SansSerif", Font.BOLD, 14));
        lblAcc.setForeground(Color.WHITE);
        centerPanel.add(lblAcc, g);

        g.gridx = 1;
        JTextField txtAccounts = new JTextField("100000");
        txtAccounts.setFont(new Font("Monospaced", Font.PLAIN, 14));
        txtAccounts.setBackground(COLOR_PANEL_DARK);
        txtAccounts.setForeground(Color.WHITE);
        txtAccounts.setCaretColor(Color.WHITE);
        centerPanel.add(txtAccounts, g);

        // Target Transactions Label & Field
        g.gridy = 2; g.gridx = 0;
        JLabel lblTxn = new JLabel("Target Transactions:");
        lblTxn.setFont(new Font("SansSerif", Font.BOLD, 14));
        lblTxn.setForeground(Color.WHITE);
        centerPanel.add(lblTxn, g);

        g.gridx = 1;
        JTextField txtTransactions = new JTextField("1000000");
        txtTransactions.setFont(new Font("Monospaced", Font.PLAIN, 14));
        txtTransactions.setBackground(COLOR_PANEL_DARK);
        txtTransactions.setForeground(Color.WHITE);
        txtTransactions.setCaretColor(Color.WHITE);
        centerPanel.add(txtTransactions, g);

        // Generation Speed
        g.gridy = 3; g.gridx = 0;
        JLabel lblSpd = new JLabel("Generation Speed Factor:");
        lblSpd.setFont(new Font("SansSerif", Font.BOLD, 14));
        lblSpd.setForeground(Color.WHITE);
        centerPanel.add(lblSpd, g);

        g.gridx = 1;
        JComboBox<String> comboSpeed = new JComboBox<>(new String[]{"1x", "10x", "50x", "100x", "1000x"});
        comboSpeed.setSelectedItem("100x");
        comboSpeed.setFont(new Font("SansSerif", Font.PLAIN, 14));
        centerPanel.add(comboSpeed, g);

        dialog.add(centerPanel, BorderLayout.CENTER);

        // Bottom Actions Panel
        JPanel actionsPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 5));
        actionsPanel.setOpaque(false);

        JButton btnStartSim = new JButton("Run Simulation (Generate New)");
        btnStartSim.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnStartSim.setBackground(COLOR_GREEN_DARK);
        btnStartSim.setForeground(Color.WHITE);
        btnStartSim.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnStartSim.addActionListener(e -> {
            dialog.dispose();
            logSystem("[COBOL] Initializing simulation stream parameters...");
            updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.STARTING);
            
            // Delete stop file if it exists
            try {
                Files.deleteIfExists(Paths.get(workspaceRoot, "runtime", "guard.stop"));
            } catch (Exception ex) {}

            customAccounts = txtAccounts.getText().trim();
            customTransactions = txtTransactions.getText().trim();
            customSpeed = comboSpeed.getSelectedItem().toString();
            manualDummyOnline = false;

            logSystem("Spawning CBS generator process (Accounts=" + customAccounts + ", Txns=" + customTransactions + ", Speed=" + customSpeed + ")...");
            startChildProcess("simulator", new String[]{"/usr/bin/env", "bash", "guard.sh"}, workspaceRoot, this::logSim);
        });

        JButton btnStartDummy = new JButton("Start Service (No New Generation)");
        btnStartDummy.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnStartDummy.setBackground(COLOR_BLUE);
        btnStartDummy.setForeground(Color.WHITE);
        btnStartDummy.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnStartDummy.addActionListener(e -> {
            dialog.dispose();
            manualDummyOnline = true;
            updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.ONLINE);
            logSystem("[COBOL] Service activated in read-only / database exposure mode (Status: ONLINE).");
            logSystem("Notice: Ready for database query transactions from the Analyst Portal.");
        });

        JButton btnCancel = new JButton("Cancel");
        btnCancel.setFont(new Font("SansSerif", Font.PLAIN, 14));
        btnCancel.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnCancel.addActionListener(e -> dialog.dispose());

        actionsPanel.add(btnStartSim);
        actionsPanel.add(btnStartDummy);
        actionsPanel.add(btnCancel);
        dialog.add(actionsPanel, BorderLayout.SOUTH);

        dialog.setVisible(true);
    }

    private void bootDockerServiceDirect(String service) {
        logSystem("Docker Compose unavailable. Attempting direct Docker container boot for: " + service);
        String containerName = "boi-" + service;
        
        // Try starting the existing container first
        boolean started = executeCommandBlocking("Docker Start " + service, new String[]{"docker", "start", containerName}, workspaceRoot);
        if (started) {
            logSystem("✓ Successfully started existing container: " + containerName);
            return;
        }
        
        // If start fails, create and run a new one
        String[] runCmd = null;
        switch (service) {
            case "neo4j":
                runCmd = new String[]{
                    "docker", "run", "-d", "--name", containerName,
                    "-p", "7474:7474", "-p", "7687:7687",
                    "-e", "NEO4J_AUTH=neo4j/fraud_detection_2026",
                    "-e", "NEO4J_PLUGINS=[\"graph-data-science\"]",
                    "-e", "NEO4J_dbms_security_procedures_unrestricted=gds.,apoc.",
                    "-e", "NEO4J_dbms_security_procedures_allowlist=gds.,apoc.",
                    "neo4j:5.18-community"
                };
                break;
            case "redis":
                runCmd = new String[]{
                    "docker", "run", "-d", "--name", containerName,
                    "-p", "6379:6379", "-p", "8001:8001",
                    "redis/redis-stack:7.2.0-v11"
                };
                break;
            case "kafka":
                runCmd = new String[]{
                    "docker", "run", "-d", "--name", containerName,
                    "-p", "9092:9092",
                    "-e", "KAFKA_NODE_ID=1",
                    "-e", "KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093",
                    "-e", "KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092",
                    "-e", "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
                    "-e", "KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:29093",
                    "-e", "KAFKA_PROCESS_ROLES=broker,controller",
                    "-e", "KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER",
                    "-e", "KAFKA_LOG_DIRS=/tmp/kraft-combined-logs",
                    "-e", "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1",
                    "-e", "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1",
                    "-e", "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1",
                    "-e", "CLUSTER_ID=MkU3OEVBNTcwNTJENDM2Qk",
                    "confluentinc/cp-kafka:7.6.0"
                };
                break;
            case "postgres":
                runCmd = new String[]{
                    "docker", "run", "-d", "--name", containerName,
                    "-p", "5432:5432",
                    "-e", "POSTGRES_USER=postgres",
                    "-e", "POSTGRES_PASSWORD=fraud_detection_2026",
                    "-e", "POSTGRES_DB=fraud_db",
                    "postgres:16-alpine"
                };
                break;
        }
        
        if (runCmd != null) {
            executeCommandBlocking("Docker Run " + service, runCmd, workspaceRoot);
        }
    }

    private void stopDockerServiceDirect(String service) {
        String containerName = "boi-" + service;
        logSystem("Stopping direct container: " + containerName);
        executeCommandBlocking("Docker Stop " + service, new String[]{"docker", "stop", containerName}, workspaceRoot);
    }

    private void bootDockerService(String service) {
        logReadingExecutor.submit(() -> {
            boolean success = false;
            if (isDockerComposeAvailable) {
                success = executeCommandBlocking("Docker Compose " + service, new String[]{"docker", "compose", "up", "-d", service}, workspaceRoot);
            } else if (isLegacyDockerComposeAvailable) {
                success = executeCommandBlocking("Docker Compose Legacy " + service, new String[]{"docker-compose", "up", "-d", service}, workspaceRoot);
            }
            if (!success) {
                // Try direct docker run fallback
                bootDockerServiceDirect(service);
            }
        });
    }

    private void shutdownDockerService(String service) {
        logReadingExecutor.submit(() -> {
            boolean success = false;
            if (isDockerComposeAvailable) {
                success = executeCommandBlocking("Docker Compose Stop " + service, new String[]{"docker", "compose", "stop", service}, workspaceRoot);
            } else if (isLegacyDockerComposeAvailable) {
                success = executeCommandBlocking("Docker Compose Stop Legacy " + service, new String[]{"docker-compose", "stop", service}, workspaceRoot);
            }
            if (!success) {
                stopDockerServiceDirect(service);
            }
        });
    }

    private boolean isDockerComposePluginAvailable() {
        try {
            Process p = Runtime.getRuntime().exec(new String[]{"docker", "compose", "version"});
            p.waitFor(1500, TimeUnit.MILLISECONDS);
            return p.exitValue() == 0;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean isLegacyDockerComposeAvailable() {
        try {
            Process p = Runtime.getRuntime().exec(new String[]{"docker-compose", "--version"});
            p.waitFor(1500, TimeUnit.MILLISECONDS);
            return p.exitValue() == 0 || p.exitValue() == 1;
        } catch (Exception e) {
            return false;
        }
    }

    private void freePort(int port) {
        logSystem("Ensuring port " + port + " is free...");
        try {
            Process p = Runtime.getRuntime().exec(new String[]{"fuser", "-k", port + "/tcp"});
            p.waitFor(2, TimeUnit.SECONDS);
        } catch (Exception e) {
            try {
                Process p = Runtime.getRuntime().exec(new String[]{"bash", "-c", "kill -9 $(lsof -t -i:" + port + ")"});
                p.waitFor(2, TimeUnit.SECONDS);
            } catch (Exception ex) {
                logSystem("Warning: Could not free port " + port + ": " + ex.getMessage());
            }
        }
    }

    // Core log function with timestamp and colorizing
    private synchronized void log(Color color, String message, boolean bold) {
        String time = new SimpleDateFormat("HH:mm:ss").format(new Date());
        String logLine = "[" + time + "] " + message;
        System.out.print(logLine);
        SwingUtilities.invokeLater(() -> {
            try {
                SimpleAttributeSet set = new SimpleAttributeSet();
                StyleConstants.setForeground(set, color);
                StyleConstants.setBold(set, bold);
                
                consoleDoc.insertString(consoleDoc.getLength(), logLine, set);
                
                // Keep cursor at the end to auto-scroll
                consolePane.setCaretPosition(consoleDoc.getLength());
            } catch (BadLocationException e) {
                System.err.println("Logging error: " + e.getMessage());
            }
        });
    }

    // High level logging with category checks
    private void logSystem(String message) {
        if (chkShowSystem.isSelected()) {
            log(COLOR_CYAN, "[SYSTEM] " + message + "\n", true);
        }
    }

    private void logBackend(String message) {
        if (chkShowBackend.isSelected()) {
            log(COLOR_AMBER, "[BACKEND] " + message + "\n", false);
        }
    }

    private void logFrontend(String message) {
        if (chkShowFrontend.isSelected()) {
            log(COLOR_BLUE, "[FRONTEND] " + message + "\n", false);
        }
    }

    private void logSim(String message) {
        if (chkShowSim.isSelected()) {
            log(COLOR_GREEN, "[SIMULATION] " + message + "\n", false);
        }
    }

    private void verifyPrerequisitesAsync() {
        logSystem("Verifying system dependencies...");
        
        CompletableFuture.runAsync(() -> {
            boolean allPassed = true;
            String[] commands = {"java", "python3", "node", "npm", "docker"};
            String[] labels = {"Java Compiler", "Python Runtime", "Node.js Platform", "NPM Package Manager", "Docker Engine"};
            
            for (int i = 0; i < commands.length; i++) {
                String cmd = commands[i];
                String label = labels[i];
                boolean ok = checkCommandExists(cmd);
                if (ok) {
                    log(COLOR_GREEN, "  ✓ " + label + " is installed\n", false);
                } else {
                    log(COLOR_RED, "  ✗ " + label + " was NOT found in system PATH!\n", true);
                    allPassed = false;
                }
            }

            // Detect Docker Compose and Legacy Docker Compose
            isDockerComposeAvailable = isDockerComposePluginAvailable();
            isLegacyDockerComposeAvailable = isLegacyDockerComposeAvailable();
            if (isDockerComposeAvailable) {
                log(COLOR_GREEN, "  ✓ Docker Compose Plugin is installed\n", false);
            } else if (isLegacyDockerComposeAvailable) {
                log(COLOR_GREEN, "  ✓ Legacy Docker Compose is installed\n", false);
            } else {
                log(COLOR_AMBER, "  ! Warning: Docker Compose is NOT installed. Direct Docker container fallback will be used.\n", true);
            }

            // Check if model weights are present
            Path weightsPath = Paths.get(workspaceRoot, "models", "xgb_fraud.json");
            if (Files.exists(weightsPath)) {
                updateServiceStatusUI(ServiceName.AI_MODELS, ServiceStatus.ONLINE);
                log(COLOR_GREEN, "  ✓ Found pre-trained machine learning models in models/ directory\n", false);
            } else {
                log(COLOR_AMBER, "  ! Warning: models/xgb_fraud.json not found on disk. AI evaluations may fail.\n", true);
            }

            if (allPassed) {
                logSystem("Prerequisites verified successfully. Ready to launch BOI Garuda Sentinel.");
            } else {
                log(COLOR_AMBER, "[SYSTEM] Pre-checks complete. Some packages are missing. Platform startup might be affected.\n", true);
            }
        });
    }

    private boolean checkCommandExists(String cmd) {
        try {
            Process p = Runtime.getRuntime().exec(new String[]{cmd, "--version"});
            p.waitFor(1500, TimeUnit.MILLISECONDS);
            return p.exitValue() == 0 || p.exitValue() == 1;
        } catch (Exception e) {
            return false;
        }
    }

    // Health Check Scheduler running every 3 seconds
    private void startHealthCheckScheduler() {
        healthCheckExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "SubsystemHealthMonitor");
            t.setDaemon(true);
            return t;
        });

        healthCheckExecutor.scheduleAtFixedRate(this::performSubsystemChecks, 3, 3, TimeUnit.SECONDS);
    }

    private void performSubsystemChecks() {
        // 1. Check Neo4j Bolt (Port 7687)
        checkSocketConnection(ServiceName.NEO4J, "localhost", 7687);

        // 2. Check Redis (Port 6379)
        checkSocketConnection(ServiceName.REDIS, "localhost", 6379);

        // 3. Check Kafka (Port 9092)
        checkSocketConnection(ServiceName.KAFKA, "localhost", 9092);

        // 4. Check Backend FastAPI (Port 8000)
        checkHttpHealth(ServiceName.BACKEND, "http://localhost:8000/");

        // 5. Check Frontend React (Port 5173)
        checkHttpHealth(ServiceName.FRONTEND, "http://localhost:5173/");

        // 6. Check COBOL / Python simulation status
        checkSimulationStatus();

        // 7. Update Swap Monitor UI metrics
        updateSwapMonitorUI();
    }

    private double[] getSwapMetrics() {
        double[] metrics = {20.0, 0.0, 0.0}; // total, used, percent
        try {
            java.util.List<String> lines = java.nio.file.Files.readAllLines(java.nio.file.Paths.get("/proc/meminfo"));
            long totalKb = 0;
            long freeKb = 0;
            for (String line : lines) {
                if (line.startsWith("SwapTotal:")) {
                    totalKb = Long.parseLong(line.replaceAll("[^0-9]", ""));
                } else if (line.startsWith("SwapFree:")) {
                    freeKb = Long.parseLong(line.replaceAll("[^0-9]", ""));
                }
            }
            if (totalKb > 0) {
                long usedKb = totalKb - freeKb;
                metrics[0] = Math.round((totalKb / (1024.0 * 1024.0)) * 100.0) / 100.0;
                metrics[1] = Math.round((usedKb / (1024.0 * 1024.0)) * 100.0) / 100.0;
                metrics[2] = Math.round(((double) usedKb / totalKb * 100.0) * 100.0) / 100.0;
            }
        } catch (Exception e) {
            // fallback
        }
        return metrics;
    }

    private void updateSwapMonitorUI() {
        double[] metrics = getSwapMetrics();
        int percent = (int) metrics[2];
        
        int protectedCount = 0;
        try {
            if (statusMap.get(ServiceName.BACKEND) == ServiceStatus.ONLINE) protectedCount++;
            if (statusMap.get(ServiceName.FRONTEND) == ServiceStatus.ONLINE) protectedCount++;
            if (statusMap.get(ServiceName.NEO4J) == ServiceStatus.ONLINE) protectedCount++;
        } catch (Exception e) {}
        
        final int finalProtectedCount = protectedCount;
        
        SwingUtilities.invokeLater(() -> {
            if (lblSwapStats != null) {
                lblSwapStats.setText(String.format("Swap Used: %.2f GB / %.2f GB (%d%%)", metrics[1], metrics[0], percent));
            }
            if (swapProgressBar != null) {
                swapProgressBar.setValue(percent);
                swapProgressBar.setString(percent + "%");
                if (percent >= 80) {
                    swapProgressBar.setForeground(COLOR_RED);
                } else if (percent >= 60) {
                    swapProgressBar.setForeground(COLOR_AMBER);
                } else {
                    swapProgressBar.setForeground(COLOR_BLUE);
                }
            }
            if (lblProtectedCount != null) {
                lblProtectedCount.setText("Protected Processes: " + finalProtectedCount + " active");
            }
        });
    }

    private void triggerManualSwapFlush() {
        logSystem("[SwapManager] Triggering aggressive swap flush...");
        CompletableFuture.runAsync(() -> {
            try {
                URL url = new URL("http://localhost:8000/api/v1/swap/flush");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setConnectTimeout(2000);
                int code = conn.getResponseCode();
                if (code == 200) {
                    logSystem("✓ Swap flush triggered successfully via API.");
                    return;
                }
            } catch (Exception ex) {
                // Ignore API error, fallback to CLI
            }
            
            Path venvPath = Paths.get(workspaceRoot, ".venv");
            String pythonBin = "python3";
            if (Files.exists(venvPath)) {
                pythonBin = venvPath.resolve("bin").resolve("python3").toString();
            }
            boolean success = executeCommandBlocking("Swap Flush Fallback",
                    new String[]{pythonBin, "-c", "from src.system.swap_manager import swap_manager; swap_manager.flush_non_critical_processes()"},
                    workspaceRoot);
            if (success) {
                logSystem("✓ Swap flush executed successfully via CLI fallback.");
            } else {
                log(COLOR_RED, "[SwapManager] Failed to trigger swap flush.\n", true);
            }
        });
    }

    private void triggerManualCacheClean() {
        logSystem("[SwapManager] Triggering deep system cache clean...");
        CompletableFuture.runAsync(() -> {
            try {
                URL url = new URL("http://localhost:8000/api/v1/swap/clean-cache");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setConnectTimeout(2000);
                int code = conn.getResponseCode();
                if (code == 200) {
                    logSystem("✓ Deep cache cleaning triggered successfully via API.");
                    return;
                }
            } catch (Exception ex) {
                // Ignore API error, fallback to CLI
            }
            
            Path venvPath = Paths.get(workspaceRoot, ".venv");
            String pythonBin = "python3";
            if (Files.exists(venvPath)) {
                pythonBin = venvPath.resolve("bin").resolve("python3").toString();
            }
            boolean success = executeCommandBlocking("Cache Clean Fallback",
                    new String[]{pythonBin, "-c", "from src.system.swap_manager import swap_manager; swap_manager.clean_system_caches()"},
                    workspaceRoot);
            if (success) {
                logSystem("✓ Deep cache cleaning executed successfully via CLI fallback.");
            } else {
                log(COLOR_RED, "[SwapManager] Failed to trigger deep cache clean.\n", true);
            }
        });
    }

    private void openSwapInspectDialog() {
        JDialog dialog = new JDialog(this, "Swap & RAM Protection Inspector", true);
        dialog.setSize(650, 550);
        dialog.setLocationRelativeTo(this);
        dialog.getContentPane().setBackground(COLOR_BG_DARK);
        dialog.setLayout(new BorderLayout(15, 15));
        ((JComponent)dialog.getContentPane()).setBorder(new EmptyBorder(20, 20, 20, 20));

        JPanel headerPanel = new JPanel(new GridLayout(2, 1, 2, 2));
        headerPanel.setOpaque(false);
        JLabel lblTitle = new JLabel("SWAP & RAM PROTECTION INSPECTOR");
        lblTitle.setFont(new Font("SansSerif", Font.BOLD, 22));
        lblTitle.setForeground(COLOR_CYAN);
        JLabel lblSub = new JLabel("Real-time kernel memory mapping and PID isolation");
        lblSub.setFont(new Font("SansSerif", Font.PLAIN, 14));
        lblSub.setForeground(COLOR_TEXT_MUTED);
        headerPanel.add(lblTitle);
        headerPanel.add(lblSub);
        dialog.add(headerPanel, BorderLayout.NORTH);

        JTextArea txtArea = new JTextArea();
        txtArea.setFont(new Font("Monospaced", Font.PLAIN, 16));
        txtArea.setBackground(COLOR_PANEL_DARK);
        txtArea.setForeground(Color.WHITE);
        txtArea.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(COLOR_BORDER_DARK, 1),
                new EmptyBorder(10, 10, 10, 10)
        ));
        txtArea.setEditable(false);

        CompletableFuture.runAsync(() -> {
            StringBuilder sb = new StringBuilder();
            sb.append("=== SYSTEM CAPABILITIES ===\n");
            
            try {
                Path venvPath = Paths.get(workspaceRoot, ".venv");
                String pythonBin = "python3";
                if (Files.exists(venvPath)) {
                    pythonBin = venvPath.resolve("bin").resolve("python3").toString();
                }
                
                ProcessBuilder pb = new ProcessBuilder(pythonBin, "-c", 
                    "from src.system.swap_manager import swap_manager; import json; print(json.dumps(swap_manager.get_status()))");
                pb.directory(new File(workspaceRoot));
                Process p = pb.start();
                BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()));
                String line = r.readLine();
                if (line != null) {
                    line = line.replace("{", "").replace("}", "").replace("\"", "").replace("[", "").replace("]", "");
                    String[] parts = line.split(",");
                    for (String part : parts) {
                        sb.append("  ").append(part.trim()).append("\n");
                    }
                } else {
                    sb.append("  Failed to extract real-time python metadata.\n");
                }
            } catch (Exception e) {
                sb.append("  Error: ").append(e.getMessage()).append("\n");
            }
            
            try {
                String swappiness = Files.readString(Paths.get("/proc/sys/vm/swappiness")).trim();
                String vfs = Files.readString(Paths.get("/proc/sys/vm/vfs_cache_pressure")).trim();
                sb.append("\n=== KERNEL TUNING ===\n");
                sb.append("  vm.swappiness: ").append(swappiness).append(" (Suggested: 85)\n");
                sb.append("  vm.vfs_cache_pressure: ").append(vfs).append(" (Suggested: 200)\n");
            } catch (Exception e) {}
            
            SwingUtilities.invokeLater(() -> txtArea.setText(sb.toString()));
        });

        JScrollPane scroll = new JScrollPane(txtArea);
        scroll.setBorder(null);
        dialog.add(scroll, BorderLayout.CENTER);

        JPanel actionPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 5));
        actionPanel.setOpaque(false);

        JButton btnSetup = new JButton("Run System setup.sh");
        btnSetup.setFont(new Font("SansSerif", Font.BOLD, 14));
        btnSetup.setBackground(COLOR_AMBER);
        btnSetup.setForeground(Color.BLACK);
        btnSetup.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnSetup.addActionListener(e -> {
            dialog.dispose();
            logSystem("Executing scripts/swap_setup.sh in a new system terminal...");
            executeCommandAsync("Swap System Setup", new String[]{"pkexec", "bash", "scripts/swap_setup.sh"}, workspaceRoot);
        });

        JButton btnClose = new JButton("Close");
        btnClose.setFont(new Font("SansSerif", Font.PLAIN, 14));
        btnClose.setCursor(new Cursor(Cursor.HAND_CURSOR));
        btnClose.addActionListener(e -> dialog.dispose());

        actionPanel.add(btnSetup);
        actionPanel.add(btnClose);
        dialog.add(actionPanel, BorderLayout.SOUTH);

        dialog.setVisible(true);
    }

    private void checkSocketConnection(ServiceName service, String host, int port) {
        // If launcher explicitly started the service and it is currently "STARTING",
        // don't stomp it back to "OFFLINE" instantly unless we want to monitor transition
        try (Socket socket = new Socket()) {
            socket.connect(new java.net.InetSocketAddress(host, port), 1000);
            updateServiceStatusUI(service, ServiceStatus.ONLINE);
        } catch (IOException e) {
            if (statusMap.get(service) != ServiceStatus.STARTING) {
                updateServiceStatusUI(service, ServiceStatus.OFFLINE);
            }
        }
    }

    private void checkHttpHealth(ServiceName service, String urlString) {
        try {
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(1000);
            conn.setReadTimeout(1000);
            int code = conn.getResponseCode();
            if (code == 200) {
                updateServiceStatusUI(service, ServiceStatus.ONLINE);
                if (service == ServiceName.BACKEND) {
                    SwingUtilities.invokeLater(() -> btnOpenDashboard.setEnabled(true));
                }
            } else {
                if (statusMap.get(service) != ServiceStatus.STARTING) {
                    updateServiceStatusUI(service, ServiceStatus.OFFLINE);
                }
            }
        } catch (Exception e) {
            if (statusMap.get(service) != ServiceStatus.STARTING) {
                updateServiceStatusUI(service, ServiceStatus.OFFLINE);
            }
        }
    }

    private boolean isProcessRunning(String pattern) {
        try {
            Process p = Runtime.getRuntime().exec(new String[]{"pgrep", "-f", pattern});
            return p.waitFor() == 0;
        } catch (Exception e) {
            return false;
        }
    }

    private void checkSimulationStatus() {
        // Verify database existence and check if transactions are increasing or if the process is alive (either spawned by launcher or manually)
        Path dbPath = Paths.get(workspaceRoot, "database", "ecosystem.db");
        Process simProc = activeProcesses.get("simulator");
        
        boolean isRunning = manualDummyOnline || (simProc != null && simProc.isAlive()) || isProcessRunning("ecosystem.py");
        
        if (isRunning && Files.exists(dbPath)) {
            updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.ONLINE);
        } else {
            if (statusMap.get(ServiceName.COBOL) != ServiceStatus.STARTING) {
                updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.OFFLINE);
            }
        }
    }

    // ----------------------------------------------------
    // LAUNCH ORCHESTRATION SEQUENCE
    // ----------------------------------------------------
    private void triggerStartSequence() {
        btnStart.setEnabled(false);
        btnStop.setEnabled(true);
        
        logSystem("Initiating Garuda platform startup sequence...");

        CompletableFuture.runAsync(() -> {
            try {
                // Step 1: Compiling COBOL legacy CBS Simulator
                logSystem("[Step 1/5] Compiling Legacy COBOL Banking Engine Simulator...");
                updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.STARTING);
                
                boolean cobolBuilt = executeCommandBlocking("Compiling COBOL", 
                        new String[]{"/usr/bin/env", "bash", "scripts/build.sh"}, 
                        workspaceRoot);
                
                if (cobolBuilt) {
                    logSystem("✓ Legacy COBOL Simulator successfully compiled directly to native binary: build/boi_banking_engine");
                } else {
                    log(COLOR_AMBER, "[SYSTEM] Warning: COBOL compiler was not found or bridge compilation failed. Running fallback simulation mode.\n", true);
                }

                // Step 2: Booting Docker Infrastructure
                logSystem("[Step 2/5] Booting up Docker container stack (Neo4j, Redis, Kafka, Postgres)...");
                updateServiceStatusUI(ServiceName.NEO4J, ServiceStatus.STARTING);
                updateServiceStatusUI(ServiceName.REDIS, ServiceStatus.STARTING);
                updateServiceStatusUI(ServiceName.KAFKA, ServiceStatus.STARTING);
                
                boolean infraBooted = false;
                if (isDockerComposeAvailable) {
                    infraBooted = executeCommandBlocking("Docker Infra", 
                            new String[]{"docker", "compose", "up", "-d"}, 
                            workspaceRoot);
                } else if (isLegacyDockerComposeAvailable) {
                    infraBooted = executeCommandBlocking("Docker Infra Legacy", 
                            new String[]{"docker-compose", "up", "-d"}, 
                            workspaceRoot);
                }
                
                if (infraBooted) {
                    logSystem("✓ Docker infrastructure booted. Awaiting socket readiness...");
                    // Wait briefly for containers to initialize
                    Thread.sleep(4000);
                } else {
                    log(COLOR_AMBER, "[SYSTEM] Docker Compose is unavailable or failed. Initializing direct container fallback boots in parallel...\n", true);
                    CompletableFuture<Void> neo4jBoot = CompletableFuture.runAsync(() -> bootDockerServiceDirect("neo4j"));
                    CompletableFuture<Void> redisBoot = CompletableFuture.runAsync(() -> bootDockerServiceDirect("redis"));
                    CompletableFuture<Void> kafkaBoot = CompletableFuture.runAsync(() -> bootDockerServiceDirect("kafka"));
                    CompletableFuture<Void> postgresBoot = CompletableFuture.runAsync(() -> bootDockerServiceDirect("postgres"));
                    CompletableFuture.allOf(neo4jBoot, redisBoot, kafkaBoot, postgresBoot).join();
                    Thread.sleep(4000);
                }

                // Step 3: Automatically Building and starting React Frontend
                logSystem("[Step 3/5] Starting React Analytic Portal...");
                freePort(5173);
                updateServiceStatusUI(ServiceName.FRONTEND, ServiceStatus.STARTING);
                
                // Let's run npm install if node_modules don't exist
                Path nodeModulesPath = Paths.get(workspaceRoot, "frontend-react", "node_modules");
                if (!Files.exists(nodeModulesPath)) {
                    logSystem("Running npm install in React directory (first-time boot)...");
                    executeCommandBlocking("NPM Install", new String[]{"npm", "install"}, workspaceRoot + "/frontend-react");
                }
                
                // Spawning Vite Dev Server asynchronously
                logSystem("Spawning Vite development server on port 5173...");
                startChildProcess("frontend", new String[]{"npm", "run", "dev"}, workspaceRoot + "/frontend-react", this::logFrontend);

                // Step 4: Starting FastAPI Backend Core
                logSystem("[Step 4/5] Booting FastAPI Fraud Intelligence Core Engine...");
                freePort(8000);
                updateServiceStatusUI(ServiceName.BACKEND, ServiceStatus.STARTING);
                
                // Check virtual env
                Path venvPath = Paths.get(workspaceRoot, ".venv");
                String pythonBin = "python3";
                if (Files.exists(venvPath)) {
                    pythonBin = venvPath.resolve("bin").resolve("python3").toString();
                }
                
                logSystem("Spawning FastAPI server at localhost:8000...");
                startChildProcess("backend", 
                        new String[]{pythonBin, "src/api/main.py"}, 
                        workspaceRoot, 
                        this::logBackend);

                // Step 5: Booting Simulation Streams (Continuous feeds) - Now manual
                logSystem("[Step 5/5] Continuous simulated feed set to manual activation mode.");
                logSystem("✓ Core systems startup sequence completed.");
                logSystem("Notice: Transaction streaming (guard.sh) should be started manually in a separate terminal.");
                
                // Ensure stop file is deleted
                Path stopFile = Paths.get(workspaceRoot, "runtime", "guard.stop");
                Files.deleteIfExists(stopFile);

                logSystem("Startup sequence triggered completely. Monitoring service readiness...");

            } catch (Exception ex) {
                log(COLOR_RED, "[SYSTEM] Critical launcher exception during startup: " + ex.getMessage() + "\n", true);
                ex.printStackTrace();
            }
        });
    }

    // ----------------------------------------------------
    // PROCESS MANAGER HELPER METHODS
    // ----------------------------------------------------
    private boolean executeCommandBlocking(String taskName, String[] cmd, String dir) {
        try {
            logSystem("Executing: " + String.join(" ", cmd) + " (working dir: " + dir + ")");
            ProcessBuilder pb = new ProcessBuilder(cmd);
            pb.directory(new File(dir));
            pb.redirectErrorStream(true);
            Process p = pb.start();

            // Read output so process doesn't hang
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    log(COLOR_TEXT_MUTED, "  [" + taskName + "] " + line + "\n", false);
                }
            }
            p.waitFor(120, TimeUnit.SECONDS);
            return p.exitValue() == 0;
        } catch (Exception ex) {
            log(COLOR_RED, "  Failed to execute task " + taskName + ": " + ex.getMessage() + "\n", true);
            return false;
        }
    }

    private void startChildProcess(String name, String[] cmd, String dir, LogConsumer logConsumer) {
        Process existing = activeProcesses.get(name);
        if (existing != null && existing.isAlive()) {
            logSystem("Process '" + name + "' is already running. Skipping duplicate spawn.");
            return;
        }
        CompletableFuture.runAsync(() -> {
            try {
                logSystem("Spawning process '" + name + "': " + String.join(" ", cmd));
                ProcessBuilder pb = new ProcessBuilder(cmd);
                pb.directory(new File(dir));
                
                // Add PYTHONPATH=. to backend environment
                if ("backend".equals(name)) {
                    pb.environment().put("PYTHONPATH", ".");
                }
                
                // Add custom simulation configs to simulator environment
                if ("simulator".equals(name)) {
                    if (customAccounts != null) pb.environment().put("BOI_ACCOUNTS", customAccounts);
                    if (customTransactions != null) pb.environment().put("BOI_TRANSACTIONS", customTransactions);
                    if (customSpeed != null) pb.environment().put("BOI_SPEED", customSpeed);
                    pb.environment().put("BOI_STOP_FILE", workspaceRoot + "/runtime/guard.stop");
                }
                
                pb.redirectErrorStream(true);
                Process p = pb.start();
                activeProcesses.put(name, p);

                // Start async reader thread for console
                logReadingExecutor.submit(() -> {
                    try (BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                        String line;
                        while ((line = reader.readLine()) != null) {
                            logConsumer.consume(line);
                        }
                    } catch (IOException ioEx) {
                        // Stream closed
                    }
                });

                int exitCode = p.waitFor();
                log(COLOR_RED, "[SYSTEM] Process '" + name + "' exited with code " + exitCode + "\n", true);
                if (activeProcesses.get(name) == p) {
                    activeProcesses.remove(name);

                    // Update UI status immediately
                    if ("frontend".equals(name)) {
                        updateServiceStatusUI(ServiceName.FRONTEND, ServiceStatus.OFFLINE);
                    } else if ("backend".equals(name)) {
                        updateServiceStatusUI(ServiceName.BACKEND, ServiceStatus.OFFLINE);
                    } else if ("simulator".equals(name)) {
                        updateServiceStatusUI(ServiceName.COBOL, ServiceStatus.OFFLINE);
                    }
                }

            } catch (Exception ex) {
                log(COLOR_RED, "[SYSTEM] Failed to spawn process '" + name + "': " + ex.getMessage() + "\n", true);
            }
        });
    }

    interface LogConsumer {
        void consume(String line);
    }

    // ----------------------------------------------------
    // SHUTDOWN & CLEANUP SEQUENCE
    // ----------------------------------------------------
    private void triggerShutdownSequence() {
        btnStop.setEnabled(false);
        logSystem("Initiating complete systems shutdown sequence...");

        CompletableFuture.runAsync(() -> {
            try {
                // Step 1: Flag simulator stop file so Python terminates cleanly
                logSystem("Sending SIGTERM signal to continuous banking simulator...");
                Path stopFile = Paths.get(workspaceRoot, "runtime", "guard.stop");
                Files.createDirectories(stopFile.getParent());
                Files.writeString(stopFile, "stop");

                // Step 2: Terminate child processes
                for (String name : activeProcesses.keySet()) {
                    Process p = activeProcesses.get(name);
                    if (p != null && p.isAlive()) {
                        logSystem("Stopping process: " + name);
                        p.descendants().forEach(ph -> {
                            try {
                                ph.destroy();
                            } catch (Exception e) {}
                        });
                        p.destroy(); // Graceful SIGTERM
                        p.waitFor(3, TimeUnit.SECONDS);
                        if (p.isAlive()) {
                            logSystem("Forcefully destroying process: " + name);
                            p.descendants().forEach(ph -> {
                                try {
                                    ph.destroyForcibly();
                                } catch (Exception e) {}
                            });
                            p.destroyForcibly(); // Force SIGKILL
                        }
                    }
                }
                activeProcesses.clear();

                // Free ports to ensure nothing is left dangling
                freePort(5173);
                freePort(8000);

                // Step 3: Run docker-compose down
                logSystem("Shutting down Docker containers...");
                boolean dockerDown = false;
                if (isDockerComposeAvailable) {
                    dockerDown = executeCommandBlocking("Docker Down", 
                            new String[]{"docker", "compose", "down"}, 
                            workspaceRoot);
                } else if (isLegacyDockerComposeAvailable) {
                    dockerDown = executeCommandBlocking("Docker Down Legacy", 
                            new String[]{"docker-compose", "down"}, 
                            workspaceRoot);
                }
                if (!dockerDown) {
                    // Direct stop fallbacks
                    stopDockerServiceDirect("neo4j");
                    stopDockerServiceDirect("redis");
                    stopDockerServiceDirect("kafka");
                    stopDockerServiceDirect("postgres");
                }
                
                logSystem("✓ Docker infrastructure stopped successfully.");

                // Force status clean
                for (ServiceName service : ServiceName.values()) {
                    if (service != ServiceName.AI_MODELS) {
                        updateServiceStatusUI(service, ServiceStatus.OFFLINE);
                    }
                }

                logSystem("Shutdown complete. All systems are OFFLINE.");
                
                SwingUtilities.invokeLater(() -> {
                    btnStart.setEnabled(true);
                    btnOpenDashboard.setEnabled(false);
                });

            } catch (Exception ex) {
                log(COLOR_RED, "[SYSTEM] Exception during clean shutdown: " + ex.getMessage() + "\n", true);
            }
        });
    }

    private void openBrowserPortal() {
        try {
            logSystem("Launching default OS browser for Analyst Web Portal...");
            if (Desktop.isDesktopSupported() && Desktop.getDesktop().isSupported(Desktop.Action.BROWSE)) {
                Desktop.getDesktop().browse(new URI("http://localhost:5173/"));
                return;
            }
        } catch (Exception ex) {
            // fallback
        }
        
        // Fallback to xdg-open on Linux
        try {
            Runtime.getRuntime().exec(new String[]{"xdg-open", "http://localhost:5173/"});
        } catch (Exception ex2) {
            try {
                Runtime.getRuntime().exec(new String[]{"sensible-browser", "http://localhost:5173/"});
            } catch (Exception ex3) {
                log(COLOR_RED, "[SYSTEM] Failed to launch default web browser: " + ex3.getMessage() + "\n", true);
            }
        }
    }

    private void handleExit() {
        if (!activeProcesses.isEmpty()) {
            int confirm = JOptionPane.showConfirmDialog(this,
                    "Active processes are running in the background. Do you want to run a complete shutdown sequence first?",
                    "Warning", JOptionPane.YES_NO_CANCEL_OPTION, JOptionPane.WARNING_MESSAGE);
            
            if (confirm == JOptionPane.YES_OPTION) {
                triggerShutdownSequence();
                // Wait briefly for shutdown async steps, then close
                CompletableFuture.runAsync(() -> {
                    try {
                        Thread.sleep(3000);
                    } catch (InterruptedException ex) {
                        // ignore
                    }
                    System.exit(0);
                });
            } else if (confirm == JOptionPane.NO_OPTION) {
                System.exit(0);
            }
        } else {
            System.exit(0);
        }
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            try {
                // Setup FlatDark Look and Feel
                UIManager.setLookAndFeel(new FlatDarkLaf());
                
                // Customize default fonts and component styling
                UIManager.put("defaultFont", new Font("SansSerif", Font.PLAIN, 20));
                UIManager.put("Button.arc", 12);
                UIManager.put("Component.arc", 12);
                UIManager.put("TextComponent.arc", 12);
                UIManager.put("ScrollBar.showButtons", true);
                UIManager.put("ScrollBar.width", 18);
                
                GarudaSentinelLauncher launcher = new GarudaSentinelLauncher();
                launcher.setVisible(true);
                
            } catch (Exception ex) {
                System.err.println("Failed to start look and feel: " + ex.getMessage());
                // Standalone Swing Fallback
                GarudaSentinelLauncher launcher = new GarudaSentinelLauncher();
                launcher.setVisible(true);
            }
        });
    }
}
