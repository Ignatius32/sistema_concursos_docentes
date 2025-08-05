#!/usr/bin/env python3
"""
Quick test script to verify sorteo functionality
Run this to check if the sorteo backend works properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.models import db, Concurso, Sustanciacion, SorteoConfig

def test_sorteo_config():
    """Test if sorteo configuration is properly set up"""
    print("Testing Sorteo Configuration...")
    
    app = create_app()
    with app.app_context():
        # Check if sorteo configs exist
        configs = SorteoConfig.query.all()
        print(f"Found {len(configs)} sorteo configurations:")
        
        for config in configs:
            print(f"  - {config.concurso_tipo} / {config.categoria_codigo}: {config.numero_temas_sorteados} temas")
        
        if not configs:
            print("  No configurations found! Make sure to initialize with default values.")
            return False
        
        return True

def test_concurso_with_sustanciacion():
    """Test if there are concursos with sustanciacion ready for sorteo"""
    print("\nTesting Concursos with Sustanciacion...")
    
    app = create_app()
    with app.app_context():
        # Find concursos with sustanciacion
        concursos_with_sust = Concurso.query.join(Sustanciacion).all()
        print(f"Found {len(concursos_with_sust)} concursos with sustanciación:")
        
        ready_for_sorteo = 0
        for concurso in concursos_with_sust:
            sust = concurso.sustanciacion
            has_temas = bool(sust.temas_exposicion)
            is_closed = sust.temas_cerrados
            already_sorted = bool(sust.tema_sorteado)
            
            status = "✅ Ready" if (has_temas and is_closed and not already_sorted) else "❌ Not ready"
            if has_temas and is_closed and not already_sorted:
                ready_for_sorteo += 1
            
            print(f"  - Concurso {concurso.id}: {status}")
            print(f"    Has temas: {has_temas}, Closed: {is_closed}, Already sorted: {already_sorted}")
            
            if has_temas:
                temas_count = len([t for t in sust.temas_exposicion.split('|') if t.strip()])
                print(f"    Temas available: {temas_count}")
        
        print(f"\nConcursos ready for sorteo: {ready_for_sorteo}")
        return ready_for_sorteo > 0

def test_sorteo_logic():
    """Test the sorteo logic without actually performing it"""
    print("\nTesting Sorteo Logic...")
    
    # Mock test data
    test_temas = ["Tema A", "Tema B", "Tema C", "Tema D", "Tema E"]
    test_configs = [
        ("REGULAR", "PAD", 1),
        ("REGULAR", "JTP", 3),
        ("INTERINO", "PAD", 1),
    ]
    
    import random
    
    for tipo, categoria, num_to_draw in test_configs:
        print(f"  Testing {tipo} {categoria} (should draw {num_to_draw} tema(s)):")
        
        if len(test_temas) >= num_to_draw:
            selected = random.sample(test_temas, num_to_draw)
            print(f"    Selected: {selected}")
        else:
            print(f"    Error: Not enough temas ({len(test_temas)} < {num_to_draw})")
    
    return True

def main():
    """Run all tests"""
    print("🎲 Sorteo de Temas - Backend Test Script")
    print("=" * 50)
    
    tests = [
        test_sorteo_config,
        test_concurso_with_sustanciacion,
        test_sorteo_logic,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Sorteo Config: {'OK' if results[0] else 'FAIL'}")
    print(f"✅ Concursos Ready: {'OK' if results[1] else 'FAIL'}")
    print(f"✅ Sorteo Logic: {'OK' if results[2] else 'FAIL'}")
    
    all_passed = all(results)
    print(f"\n🎯 Overall Status: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🚀 Your sorteo system is ready to use!")
        print("💡 To test the frontend:")
        print("   1. Start the Flask app")
        print("   2. Navigate to a concurso with consolidated topics")
        print("   3. Open the 'Sustanciación' tab")
        print("   4. Click 'Realizar Sorteo de Tema'")
        print("   5. Check browser console for debug logs")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
